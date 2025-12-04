from common.comms.node_client import AlarmNode
from common.comms.protocol import AlarmEvent, EventType, Alarm
import time

def main():
    node = AlarmNode()
    node.start_discovery()  # Zeroconf discovery

    print("[NODE APP] Waiting for host...")

    # Wait until the node connects
    while not node.connected:
        time.sleep(0.2)

    print("[NODE APP] Connected to host!")

    # Send a heartbeat to host
    hb = AlarmEvent(EventType.HEARTBEAT, {"node_id": "demo"})
    node.send(hb)

    try:
        while True:
            time.sleep(10)  # Send heartbeat every 30 seconds instead of every 1 second

            # Send a heartbeat
            hb = AlarmEvent(EventType.HEARTBEAT)
            node.send(hb)

    except KeyboardInterrupt:
        print("[NODE APP] Shutting down")
        node.stop()

if __name__ == "__main__":
    main()
