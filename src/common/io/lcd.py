
from RPLCD.i2c import CharLCD
import time

# Common I2C addresses: 0x27 or 0x3F
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1,
    cols=16, rows=2, charmap='A00')

def lcd_write(text: str):
    lcd.clear()
    # Simple 2-line wrap for 16x2
    line1 = text[:16].ljust(16)
    line2 = text[16:32].ljust(16)
    lcd.write_string(line1)
    lcd.cursor_pos = (1, 0)
    lcd.write_string(line2)

lcd_write("Hello LCD! This wraps onto line 2.")
time.sleep(5)
lcd.clear()
lcd.close()
