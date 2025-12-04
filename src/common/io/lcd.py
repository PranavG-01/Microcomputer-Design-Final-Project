from RPLCD.gpio import CharLCD
import RPi.GPIO as GPIO
import time

class LCD:
    def __init__(self):
        self.lcd = CharLCD(
            pin_rs=24, pin_e=23, pins_data=[17, 18, 27, 22],
            numbering_mode=GPIO.BCM, cols=16, rows=2, dotsize=8
        )

    def lcd_write(self, curTime, alarmSet):
        self.lcd.cursor_pos = (0, 0)
        self.lcd.write_string(curTime)
        self.lcd.cursor_pos = (1, 0)
        if alarmSet == True:
            self.lcd.write_string("Alarm On")
        else:
            self.lcd.write_string("Alarm Off")

    def lcd_clearScreen(self):
        self.lcd.clear()

    def close(self):
        self.lcd.clear()
        self.lcd.close()
        GPIO.cleanup()

# Test Main
'''
if __name__ == "__main__":
    screen = LCD()
    try:
        screen.lcd_clearScreen()
        screen.lcd_write("12:34", True)
        time.sleep(3)
        screen.lcd_write("09:10", False)
        time.sleep(3)
    finally:
        screen.close()
'''
