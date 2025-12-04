from common.comms.host_server import AlarmHost
from host.alarm_manager import AlarmManager
from common.comms.protocol import Alarm, AlarmEvent, EventType
from common.io.lcd import LCD
from common.io.time_display import TimeDisplay
from common.io.buzzer import BuzzerController
from common.io.button import SnoozeButton

from flask import Flask, render_template
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired
from wtforms_components import TimeField
from datetime import datetime

import time
import threading

host = None
alarm_manager = None
lcd = None
buzzer = None
button = None

app = Flask(__name__)
app.config['SECRET_KEY'] = "secretkey"

class AlarmTime(FlaskForm):
    time = TimeField('Time', validators = [InputRequired()])
    submit = SubmitField("Set Alarm")

@app.route("/", methods = ["GET", "POST"])
def index():
    form = AlarmTime()
    if form.validate_on_submit():
        t = form.time.data
        # Convert the submitted time (a datetime.time) to our Alarm (12-hour format)
        hour24 = t.hour
        minute = t.minute
        # Convert 24-hour to 12-hour + is_pm flag
        if hour24 == 0:
            hour12 = 12
            is_pm = False
        elif 1 <= hour24 < 12:
            hour12 = hour24
            is_pm = False
        elif hour24 == 12:
            hour12 = 12
            is_pm = True
        else:
            hour12 = hour24 - 12
            is_pm = True

        alarm = Alarm(hours=hour12, minutes=minute, is_pm=is_pm)
        if alarm_manager:
            alarm_manager.set_alarm(alarm)
            msg = f"Alarm set for {alarm}"
            # Update LCD immediately so display doesn't wait for the next minute tick
            try:
                if lcd:
                    display_now = TimeDisplay(current_time=datetime.now(), alarm=alarm)
                    lcd.write(display_now.get_time_line(), display_now.get_alarm_line())
            except Exception as e:
                print(f"[HOST APP] Failed to update LCD after setting alarm: {e}")
        else:
            msg = f"Alarm created (server not running): {alarm}"

        return render_template("index.html", form=form, message=msg, current_alarm=alarm)
    return render_template("index.html", form = form)


def handle_event(event: AlarmEvent, addr):
    """Handle received events from nodes"""
    if event.type == EventType.SNOOZE_PRESSED:
        alarm_manager.handle_snooze(addr, host.get_connected_nodes_count())


def button_monitor():
    """Monitor button presses while alarm is active"""
    while host and host.running:
        try:
            if alarm_manager.is_alarm_active() and button:
                if button.is_pressed():
                    print("[HOST] Snooze button pressed")
                    alarm_manager.handle_host_snooze()
                    # Debounce: wait for release
                    time.sleep(0.5)
            time.sleep(0.05)  # Poll every 50ms
        except Exception as e:
            print(f"[HOST] Error in button monitor: {e}")
            time.sleep(0.05)


def update_display():
    """Update LCD display every minute with current time and alarm status"""
    while host and host.running:
        try:
            current_time = datetime.now()
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
        
        current_time = datetime.now()
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
    global host, alarm_manager, lcd, buzzer, button
    host = AlarmHost(port=5001, event_handler=handle_event)
    alarm_manager = AlarmManager(event_callback=host.broadcast)
    
    # Start Flask web server in a background thread so the form works
    try:
        flask_thread = threading.Thread(
            target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False),
            daemon=True,
        )
        flask_thread.start()
        print("[HOST APP] Flask webserver started on port 5000")
    except Exception as e:
        print(f"[HOST APP] Failed to start Flask webserver: {e}")

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
    
    # Initialize button
    try:
        button = SnoozeButton(button_pin=10)  # Adjust pin as needed
        print("[HOST APP] Button initialized")
    except Exception as e:
        print(f"[HOST APP] Failed to initialize Button: {e}")
    
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

    # Start the button monitor thread
    button_thread = threading.Thread(target=button_monitor, daemon=True)
    button_thread.start()

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
        if button:
            button.close()
        host.stop()

if __name__ == "__main__":
    main()
