from flask import Flask, send_from_directory
from common.comms.host_server import AlarmHost
from host.alarm_manager import AlarmManager
from common.comms.protocol import Alarm, AlarmEvent, EventType
import time
import threading
import datetime

app = Flask(__name__)
host = None
alarm_manager = None

@app.route("/")
def home():
    return "Test"


def handle_event(event: AlarmEvent, addr):
    """Handle received events from nodes"""
    if event.type == EventType.SNOOZE_PRESSED:
        alarm_manager.handle_snooze(addr, host.get_connected_nodes_count())


def alarm_scheduler():
    """Monitor scheduled alarm and trigger it at the right time"""
    while host and host.running:
        time.sleep(1)  # Check every second
        
        if alarm_manager.is_alarm_active():
            continue  # Skip if an alarm is already active
        
        alarm = alarm_manager.get_current_alarm()
        if not alarm:
            continue  # Skip if no alarm set
        
        current_time = datetime.datetime.now()
        hour_24, minute = alarm.get_24hr_time()
        alarm_time = current_time.replace(
            hour=hour_24,
            minute=minute,
            second=0,
            microsecond=0
        )
        
        # Check if we're within 1 second of the alarm time
        if abs((current_time - alarm_time).total_seconds()) < 1:
            alarm_manager.trigger_alarm(alarm)


def main():
    global host, alarm_manager
    host = AlarmHost(port=5001, event_handler=handle_event)
    alarm_manager = AlarmManager(event_callback=host.broadcast)
    host.start()

    print("[HOST APP] Host is running.")
    time.sleep(2)

    # Set the alarm for 2:10 PM
    alarm = Alarm(hours=2, minutes=25, is_pm=True)
    alarm_manager.set_alarm(alarm)

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
