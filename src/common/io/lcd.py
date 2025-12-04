from RPLCD import CharLCD
from RPi import GPIO
import time 

lcd = CharLCD(pin_rs=24, pin_e=23, pins_data=[17, 18, 27, 22],
    numbering_mode=GPIO.BCM, cols=16, rows=2, dotsize=8)

def lcd_write(curTime, alarmSet):
    lcd.cursor_pos = (0,0)
    lcd.write_string(curTime)
    lcd.cursor_pos = (1,0)
    if alarmSet == True:
        lcd.write_string("Alarm On")
    else:
        lcd.write_string("Alarm Off")

def lcd_clearScreen():
    lcd.clear()

if __name__ == "__main__":
    try:
        lcd.clear()

        lcd_write("12:34", True)
        time.sleep(3)

        lcd_write("09:10", False)
        time.sleep(3)

        lcd_clearScreen()
        time.sleep(1)

    finally:
        lcd.clear()
        lcd.close()
        GPIO.cleanup()
