from RPLCD.gpio import CharLCD
import RPi.GPIO as GPIO
import time


class LCD:
    def __init__(self):
        # Ensure GPIO is in BCM mode and pins are configured as outputs
        GPIO.setmode(GPIO.BCM)
        pins = [24, 23, 17, 18, 27, 22]
        for p in pins:
            try:
                GPIO.setup(p, GPIO.OUT)
            except RuntimeError:
                # If pins are already set up or restricted, ignore
                pass

        self.lcd = CharLCD(
            pin_rs=24, pin_e=23, pins_data=[17, 18, 27, 22],
            numbering_mode=GPIO.BCM, cols=16, rows=2, dotsize=8
        )

    def write(self, line1: str, line2: str = ""):
        """
        Write two lines to the LCD display.
        
        Args:
            line1: String for line 1 (max 16 chars)
            line2: String for line 2 (max 16 chars), optional
        """
        # Truncate to fit 16 character width
        line1 = str(line1)[:16]
        line2 = str(line2)[:16]
        
        self.lcd.cursor_pos = (0, 0)
        self.lcd.write_string(line1)
        self.lcd.cursor_pos = (1, 0)
        self.lcd.write_string(line2)

    def clear(self):
        self.lcd.clear()

    def close(self):
        self.lcd.clear()
        try:
            self.lcd.close()
        except Exception:
            pass
        try:
            GPIO.cleanup()
        except Exception:
            pass