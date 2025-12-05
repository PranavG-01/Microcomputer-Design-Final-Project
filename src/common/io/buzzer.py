import RPi.GPIO as GPIO
import time
import threading

# Global flag to ensure GPIO.setmode is called only once
_GPIO_MODE_SET = False

def _ensure_gpio_mode():
    global _GPIO_MODE_SET
    if not _GPIO_MODE_SET:
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            _GPIO_MODE_SET = True
        except Exception:
            pass

class BuzzerController:
    """Simple buzzer controller using RPi.GPIO"""
    
    def __init__(self, buzzer_pin):
        _ensure_gpio_mode()
        self.pin = buzzer_pin
        self.is_on = False
        self._beep_thread = None
        
        try:
            GPIO.setup(buzzer_pin, GPIO.OUT)
        except Exception:
            pass  # Pin may already be set up

    def turn_on(self):
        """Turn on the buzzer with a beeping pattern"""
        if self.is_on:
            return
        
        self.is_on = True
        # Start beeping in a background thread so it doesn't block
        self._beep_thread = threading.Thread(target=self._beep_pattern, daemon=True)
        self._beep_thread.start()

    def turn_off(self):
        """Turn off the buzzer"""
        self.is_on = False
        try:
            GPIO.output(self.pin, GPIO.LOW)
        except Exception:
            pass

    def _beep_pattern(self):
        """Generate a repeating beep pattern while is_on is True"""
        while self.is_on:
            try:
                # Short beep
                GPIO.output(self.pin, GPIO.HIGH)
                time.sleep(0.2)
                GPIO.output(self.pin, GPIO.LOW)
                time.sleep(0.2)
            except Exception:
                break

    def close(self):
        """Clean up GPIO resources"""
        self.turn_off()
        try:
            GPIO.cleanup(self.pin)
        except Exception:
            pass
