from zeroconf import ServiceBrowser, ServiceStateChange

class AlarmNode:
    def __init__(self):
        self.zeroconf = Zeroconf()
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

        # Host disappeared
        elif state_change == ServiceStateChange.Removed:
            print("[NODE] Host disappeared.")
            self.host_ip = None
            self.host_port = None

    def _decode_ip(self, info):
        return ".".join(str(b) for b in info.addresses[0])
