from RPLCD.gpio import CharLCD
import RPi.GPIO as GPIO
import time
from common.comms.protocol import Alarm

class LCD:
    def __init__(self):
        self.lcd = CharLCD(
            pin_rs=24, pin_e=23, pins_data=[17, 18, 27, 22],
            numbering_mode=GPIO.BCM, cols=16, rows=2, dotsize=8
        )

    def lcd_write(self, current_time, alarm=None):
        """
        Write to LCD display.
        
        Args:
            current_time: datetime object for current time
            alarm: Alarm object or None
        
        Displays format:
        Line 1: Current time in 12-hour format (e.g., "2:30 PM")
        Line 2: Alarm time if set (e.g., "Alarm: 7:30 AM"), else "No Alarm"
        """
        # Format current time in 12-hour format
        time_12hr = current_time.strftime("%I:%M %p")
        # Remove leading zero from hour (strftime %I gives 01-12)
        if time_12hr[0] == '0':
            time_12hr = time_12hr[1:]
        
        # Format alarm info
        if alarm:
            alarm_str = f"Alarm: {alarm}"
        else:
            alarm_str = "No Alarm"
        
        # Ensure strings fit in 16 character width
        time_12hr = time_12hr[:16]
        alarm_str = alarm_str[:16]
        
        self.lcd.cursor_pos = (0, 0)
        self.lcd.write_string(time_12hr)
        self.lcd.cursor_pos = (1, 0)
        self.lcd.write_string(alarm_str)

    def lcd_clearScreen(self):
        self.lcd.clear()

    def close(self):
        self.lcd.clear()
        self.lcd.close()
        GPIO.cleanup()