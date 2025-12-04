from flask import Flask, send_from_directory
from common.comms.host_server import AlarmHost
from common.comms.protocol import Alarm
import time
import threading
import datetime

app = Flask(__name__)
host = None

@app.route("/")
def home():
    return "Test"


def alarm_scheduler():
    """Monitor scheduled alarm and trigger it at the right time"""
    while host and host.running:
        time.sleep(1)  # Check every second
        
        with host.lock:
            if not host.current_alarm or host.alarm_active:
                continue  # Skip if no alarm set or one is already active
            
            alarm = host.current_alarm
            current_time = datetime.datetime.now()
            alarm_time = current_time.replace(
                hour=alarm.hours,
                minute=alarm.minutes,
                second=0,
                microsecond=0
            )
            
            # Check if we're within 1 second of the alarm time
            if abs((current_time - alarm_time).total_seconds()) < 1:
                host.trigger_alarm(alarm)


def main():
    global host
    host = AlarmHost(port=5001)
    host.start()

    print("[HOST APP] Host is running.")
    time.sleep(2)

    # Set the alarm for 7:30 AM
    alarm = Alarm(hours=2, minutes=10, is_pm=True)
    host.set_alarm(alarm)

    # Start the alarm scheduler thread
    scheduler_thread = threading.Thread(target=alarm_scheduler, daemon=True)
    scheduler_thread.start()

    # Keep alive forever
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[HOST APP] Stopping")
        host.stop()

if __name__ == "__main__":
    main()
