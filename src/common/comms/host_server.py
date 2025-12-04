# alarm_host.py
import socket
import threading
from zeroconf import Zeroconf, ServiceInfo
from alarm_packet import AlarmEvent, EventType


class AlarmHost:
    SERVICE_TYPE = "_alarmhost._tcp.local."
    SERVICE_NAME = "AlarmHostService._alarmhost._tcp.local."

    def __init__(self, port=5001):
        self.port = port
        self.zeroconf = Zeroconf()
        self.service_info = None
        self.clients = []      # (conn, addr)
        self.running = False

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

    def _accept_loop(self):
        while self.running:
            conn, addr = self.sock.accept()
            print(f"[HOST] Node connected from {addr}")
            self.clients.append((conn, addr))

            threading.Thread(
                target=self._client_recv_loop, 
                args=(conn, addr),
                daemon=True
            ).start()

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
                    print(f"[HOST] Received from {addr}: {event}")
            except:
                break

        print(f"[HOST] Node disconnected {addr}")
        conn.close()

    # ------------------------------
    # Sending events
    # ------------------------------
    def broadcast(self, event: AlarmEvent):
        msg = event.to_json() + "\n"
        print(f"[HOST] Broadcasting: {event}")
        for conn, _ in self.clients:
            try:
                conn.sendall(msg.encode())
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
        for conn, _ in self.clients:
            conn.close()
        self.sock.close()
