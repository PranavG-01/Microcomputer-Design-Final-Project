from flask import Flask, send_from_directory
from common.comms.host_server import AlarmHost, AlarmEvent
from common.comms.protocol import EventType
import time

app = Flask(__name__)

@app.route("/")
def home():
    return "Test"


def main():
    host = AlarmHost(port=5001)
    host.start()

    print("[HOST APP] Host is running.")
    time.sleep(2)

    # Example: broadcast an alarm triggered event
    event = AlarmEvent(EventType.ALARM_TRIGGERED, {"reason": "demo"})
    host.broadcast(event)

    # Keep alive forever
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[HOST APP] Stopping")
        host.stop()

if __name__ == "__main__":
    main()
