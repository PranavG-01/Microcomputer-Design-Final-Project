from flask import Flask, send_from_directory
from common.comms.host_server import AlarmHost
from host.alarm_manager import AlarmManager
from common.comms.protocol import Alarm, AlarmEvent, EventType
from common.io.lcd import LCD
from common.io.time_display import TimeDisplay
from common.io.buzzer import BuzzerController
import time
import threading
import datetime

app = Flask(__name__)
host = None
alarm_manager = None
lcd = None
buzzer = None

@app.route("/")
def home():
    return "Test"


def handle_event(event: AlarmEvent, addr):
    """Handle received events from nodes"""
    if event.type == EventType.SNOOZE_PRESSED:
        alarm_manager.handle_snooze(addr, host.get_connected_nodes_count())


def update_display():
    """Update LCD display every minute with current time and alarm status"""
    while host and host.running:
        try:
            current_time = datetime.datetime.now()
            alarm = alarm_manager.get_current_alarm()
            
            # Create a TimeDisplay object with current time and alarm
            display = TimeDisplay(current_time=current_time, alarm=alarm)
            
            if lcd:
                lcd.write(display.get_time_line(), display.get_alarm_line())
            
            print(f"[HOST] Display updated: {display}")
            
            # Update every minute (60 seconds)
            time.sleep(60)
        except Exception as e:
            print(f"[HOST] Error updating display: {e}")
            time.sleep(60)


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
    global host, alarm_manager, lcd, buzzer
    host = AlarmHost(port=5001, event_handler=handle_event)
    alarm_manager = AlarmManager(event_callback=host.broadcast)
    
    # Initialize LCD and Buzzer
    try:
        lcd = LCD()
        print("[HOST APP] LCD initialized")
    except Exception as e:
        print(f"[HOST APP] Failed to initialize LCD: {e}")
    
    try:
        buzzer = BuzzerController(buzzer_pin=4)  # Adjust pin as needed
        print("[HOST APP] Buzzer initialized")
    except Exception as e:
        print(f"[HOST APP] Failed to initialize Buzzer: {e}")
    
    host.start()

    print("[HOST APP] Host is running.")
    time.sleep(2)

    # Set the alarm for 2:25 PM
    # alarm = Alarm(hours=2, minutes=25, is_pm=True)
    # alarm_manager.set_alarm(alarm)

    # Start the alarm scheduler thread
    scheduler_thread = threading.Thread(target=alarm_scheduler, daemon=True)
    scheduler_thread.start()

    # Start the display update thread
    display_thread = threading.Thread(target=update_display, daemon=True)
    display_thread.start()

    # Keep alive forever
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[HOST APP] Stopping")
        if lcd:
            lcd.close()
        if buzzer:
            buzzer.turn_off()
        host.stop()

if __name__ == "__main__":
    main()
