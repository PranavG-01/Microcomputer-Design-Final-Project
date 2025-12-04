from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf
import socket
import json
from common.comms.protocol import AlarmEvent

class AlarmNode:
    def __init__(self):
        self.zeroconf = Zeroconf()
        self.browser = None
        self.host_ip = None
        self.host_port = None
        self.socket = None
        self.connected = False
        print("[NODE] Initialized")

    def start_discovery(self):
        """Start discovering the host via Zeroconf"""
        self.browser = ServiceBrowser(
            self.zeroconf,
            "_alarmhost._tcp.local.",
            handlers=[self._on_service_state_change]
        )
        print("[NODE] Searching for host...")

    def _on_service_state_change(self, zeroconf, service_type, name, state_change):
        print(f"[DEBUG] Zeroconf change: {name} -> {state_change}")

        # Host appeared
        if state_change == ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                self.host_ip = self._decode_ip(info)
                self.host_port = info.port
                print(f"[NODE] Found host at {self.host_ip}:{self.host_port}")
                self._connect_to_host()

        # Host disappeared
        elif state_change == ServiceStateChange.Removed:
            print("[NODE] Host disappeared.")
            self.host_ip = None
            self.host_port = None
            self.connected = False

    def _decode_ip(self, info):
        return ".".join(str(b) for b in info.addresses[0])

    def _connect_to_host(self):
        """Connect to the host via TCP"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host_ip, self.host_port))
            self.connected = True
            print(f"[NODE] Connected to host at {self.host_ip}:{self.host_port}")
        except Exception as e:
            print(f"[NODE] Failed to connect to host: {e}")
            self.connected = False

    def send(self, event: AlarmEvent):
        """Send an alarm event to the host"""
        if not self.connected or self.socket is None:
            print("[NODE] Not connected to host, cannot send event")
            return
        try:
            message = event.to_json()
            self.socket.sendall((message + "\n").encode())
            print(f"[NODE] Sent event: {event.type.name}")
        except Exception as e:
            print(f"[NODE] Failed to send event: {e}")
            self.connected = False

    def stop(self):
        """Stop the node and close connections"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        if self.browser:
            self.browser.cancel()
        if self.zeroconf:
            self.zeroconf.close()
        self.connected = False
        print("[NODE] Stopped")
