# alarm_host.py
import socket
import threading
import time
from zeroconf import Zeroconf, ServiceInfo
from common.comms.protocol import AlarmEvent, EventType

class AlarmHost:
    SERVICE_TYPE = "_alarmhost._tcp.local."
    SERVICE_NAME = "AlarmHostService._alarmhost._tcp.local."
    HEARTBEAT_TIMEOUT = 60  # Remove node if no heartbeat for 60 seconds

    def __init__(self, port=5001, event_handler=None, on_node_connected=None):
        self.port = port
        self.zeroconf = Zeroconf()
        self.service_info = None
        self.clients = {}      # {addr: {"conn": conn, "last_heartbeat": timestamp}}
        self.running = False
        self.lock = threading.Lock()
        self.event_handler = event_handler  # Callback for handling received events
        self.on_node_connected = on_node_connected  # Callback when a node connects

    # ------------------------------
    # Zeroconf Service Announce
    # ------------------------------
    def start_advertising(self):
        # Try to find a non-loopback LAN IP. socket.gethostbyname(hostname)
        # often returns 127.0.1.1 on some systems, which makes the advertised
        # address unreachable for other devices. Use a UDP trick to discover
        # the primary outbound IP and fall back gracefully.
        ip = None
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # This doesn't need to be reachable; no packets are sent.
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            try:
                ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                ip = "127.0.0.1"
        finally:
            try:
                if s:
                    s.close()
            except:
                pass

        self.service_info = ServiceInfo(
            type_=self.SERVICE_TYPE,
            name=self.SERVICE_NAME,
            addresses=[socket.inet_aton(ip)],
            port=self.port,
            properties={"role": "host"}
        )

        self.zeroconf.register_service(self.service_info)
        print(f"[HOST] Advertised service at {ip}:{self.port}")

    # ------------------------------
    # TCP Server
    # ------------------------------
    def start_tcp_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("", self.port))
        self.sock.listen(5)
        print(f"[HOST] TCP server listening on port {self.port}")

        threading.Thread(target=self._accept_loop, daemon=True).start()
        threading.Thread(target=self._heartbeat_monitor, daemon=True).start()

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.sock.accept()
                print(f"[HOST] Node connected from {addr}")
                with self.lock:
                    self.clients[addr] = {
                        "conn": conn,
                        "last_heartbeat": time.time()
                    }
                
                # Notify that a node connected (so we can send current alarm state)
                if self.on_node_connected:
                    self.on_node_connected(addr, conn)

                threading.Thread(
                    target=self._client_recv_loop, 
                    args=(conn, addr),
                    daemon=True
                ).start()
            except:
                pass

    def _client_recv_loop(self, conn, addr):
        buffer = ""
        while self.running:
            try:
                data = conn.recv(4096).decode()
                if not data:
                    break
                buffer += data

                # Messages separated by newline
                while "\n" in buffer:
                    packet, buffer = buffer.split("\n", 1)
                    event = AlarmEvent.from_json(packet)
                    print(f"[HOST] Received from {addr}: {event.type.name}")
                    
                    # Update heartbeat timestamp if it's a heartbeat
                    if event.type == EventType.HEARTBEAT:
                        with self.lock:
                            if addr in self.clients:
                                self.clients[addr]["last_heartbeat"] = time.time()
                    
                    # Delegate to event handler if provided
                    if self.event_handler:
                        self.event_handler(event, addr)
            except:
                break

        print(f"[HOST] Node disconnected {addr}")
        conn.close()
        with self.lock:
            if addr in self.clients:
                del self.clients[addr]

    def _heartbeat_monitor(self):
        """Monitor heartbeats and remove nodes that have timed out"""
        while self.running:
            time.sleep(10)  # Check every 10 seconds
            current_time = time.time()
            
            with self.lock:
                dead_nodes = [
                    addr for addr, info in self.clients.items()
                    if current_time - info["last_heartbeat"] > self.HEARTBEAT_TIMEOUT
                ]
                
                for addr in dead_nodes:
                    print(f"[HOST] Node {addr} timed out (no heartbeat). Removing...")
                    try:
                        self.clients[addr]["conn"].close()
                    except:
                        pass
                    del self.clients[addr]

    # ------------------------------
    # Sending events
    # ------------------------------
    def broadcast(self, event: AlarmEvent):
        msg = event.to_json() + "\n"
        print(f"[HOST] Broadcasting: {event.type.name}")
        with self.lock:
            for addr, info in self.clients.items():
                try:
                    info["conn"].sendall(msg.encode())
                except:
                    pass

    def get_connected_nodes_count(self) -> int:
        """Get the number of currently connected nodes"""
        with self.lock:
            return len(self.clients)

    # ------------------------------
    # Control
    # ------------------------------
    def start(self):
        self.running = True
        self.start_advertising()
        self.start_tcp_server()

    def stop(self):
        print("[HOST] Stopping host...")
        self.running = False
        self.zeroconf.unregister_service(self.service_info)
        self.zeroconf.close()
        with self.lock:
            for addr, info in self.clients.items():
                try:
                    info["conn"].close()
                except:
                    pass
        try:
            self.sock.close()
        except:
            pass
