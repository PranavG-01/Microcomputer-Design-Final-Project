# alarm_host.py
import socket
import threading
import time
from zeroconf import Zeroconf, ServiceInfo
from common.comms.protocol import AlarmEvent, EventType, Alarm


class AlarmHost:
    SERVICE_TYPE = "_alarmhost._tcp.local."
    SERVICE_NAME = "AlarmHostService._alarmhost._tcp.local."
    HEARTBEAT_TIMEOUT = 60  # Remove node if no heartbeat for 60 seconds

    def __init__(self, port=5001):
        self.port = port
        self.zeroconf = Zeroconf()
        self.service_info = None
        self.clients = {}      # {addr: {"conn": conn, "last_heartbeat": timestamp}}
        self.running = False
        self.lock = threading.Lock()
        
        # Alarm state management
        self.current_alarm = None  # Single Alarm object scheduled
        self.alarm_active = False  # Is an alarm currently triggered?
        self.snooze_responses = set()  # Addresses that have sent snooze

    # ------------------------------
    # Zeroconf Service Announce
    # ------------------------------
    def start_advertising(self):
        ip = socket.gethostbyname(socket.gethostname())

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
        self.sock.bind(("0.0.0.0", self.port))
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
                    
                    # Handle other event types (alarms, etc.)
                    self._handle_event(event, addr)
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

    def _handle_event(self, event: AlarmEvent, addr):
        """Handle received events"""
        if event.type == EventType.SNOOZE_PRESSED:
            print(f"[HOST] Snooze pressed by {addr}")
            with self.lock:
                self.snooze_responses.add(addr)
                # Check if all nodes have sent snooze
                if len(self.snooze_responses) == len(self.clients):
                    print(f"[HOST] All nodes have snoozed. Alarm cleared.")
                    self._clear_alarm()

    # ------------------------------
    # Alarm Management
    # ------------------------------
    def set_alarm(self, alarm: Alarm):
        """Set the alarm to be scheduled"""
        with self.lock:
            self.current_alarm = alarm
        print(f"[HOST] Alarm scheduled for {alarm}")

    def trigger_alarm(self, alarm: Alarm):
        """Trigger an alarm and broadcast to all nodes"""
        with self.lock:
            if self.alarm_active:
                print("[HOST] An alarm is already active, ignoring new trigger")
                return
            
            self.alarm_active = True
            self.snooze_responses.clear()
        
        print(f"[HOST] ALARM TRIGGERED for {alarm.hours}:{alarm.minutes:02d}")
        event = AlarmEvent(
            EventType.ALARM_TRIGGERED,
            {"alarm": alarm.to_dict()},
            expires_at=alarm.get_next_trigger_time()
        )
        self.broadcast(event)

    def _clear_alarm(self):
        """Clear the active alarm"""
        with self.lock:
            self.alarm_active = False
            self.snooze_responses.clear()
        
        print("[HOST] Alarm cleared, resetting for next scheduled alarm")
        event = AlarmEvent(EventType.ALARM_CLEARED, {"reason": "all nodes snoozed"})
        self.broadcast(event)

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
