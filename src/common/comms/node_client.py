# alarm_node.py
import socket
import threading
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
from .protocol import AlarmEvent


class AlarmNode:
    SERVICE_TYPE = "_alarmhost._tcp.local."

    def __init__(self):
        self.zeroconf = Zeroconf()
        self.host_info = None
        self.sock = None
        self.connected = False

    # ------------------------------
    # Zeroconf Discovery
    # ------------------------------
    def start_discovery(self):
        print("[NODE] Searching for host...")
        ServiceBrowser(
            self.zeroconf,
            self.SERVICE_TYPE,
            handlers=[self._on_service_state_change]
        )

    def _on_service_state_change(self, zc, service_type, name, state_change):
        if state_change is ServiceStateChange.Added:
            info = zc.get_service_info(service_type, name)
            if info:
                ip = ".".join(map(str, info.addresses[0]))
                print(f"[NODE] Host found at {ip}:{info.port}")
                self.host_info = info
                self.connect_to_host(ip, info.port)

    # ------------------------------
    # TCP Client Connection
    # ------------------------------
    def connect_to_host(self, ip, port):
        if self.connected:
            return

        print("[NODE] Connecting to host...")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((ip, port))
        self.connected = True

        threading.Thread(target=self._recv_loop, daemon=True).start()

    def _recv_loop(self):
        buffer = ""
        while self.connected:
            try:
                data = self.sock.recv(4096).decode()
                if not data:
                    break
                buffer += data

                while "\n" in buffer:
                    packet, buffer = buffer.split("\n", 1)
                    event = AlarmEvent.from_json(packet)
                    print(f"[NODE] Received: {event}")
            except:
                break

        print("[NODE] Disconnected from host")
        self.connected = False

    # ------------------------------
    # Sending events
    # ------------------------------
    def send(self, event: AlarmEvent):
        if self.connected:
            msg = event.to_json() + "\n"
            print(f"[NODE] Sending: {event}")
            self.sock.sendall(msg.encode())

    # ------------------------------
    # Shutdown
    # ------------------------------
    def stop(self):
        print("[NODE] Stopping node...")
        self.connected = False
        if self.sock:
            self.sock.close()
        self.zeroconf.close()
