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
    """Buzzer controller using RPi.GPIO with PWM for passive buzzers"""
    
    def __init__(self, buzzer_pin, frequency=1000):
        """
        Initialize buzzer controller.
        
        Args:
            buzzer_pin: GPIO pin number for the buzzer
            frequency: PWM frequency in Hz (default 1000 for passive buzzer)
        """
        _ensure_gpio_mode()
        self.pin = buzzer_pin
        self.frequency = frequency
        self.is_on = False
        self._pwm = None
        self._beep_thread = None
        
        try:
            GPIO.setup(buzzer_pin, GPIO.OUT)
            self._pwm = GPIO.PWM(buzzer_pin, frequency)
        except Exception as e:
            print(f"[BUZZER] Failed to initialize PWM: {e}")

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
            if self._pwm:
                self._pwm.stop()
        except Exception:
            pass

    def _beep_pattern(self):
        """Generate a repeating beep pattern using PWM while is_on is True"""
        if not self._pwm:
            return
        
        while self.is_on:
            try:
                self._pwm.start(20)  # 20% duty cycle
                time.sleep(0.3)  # Beep for 300ms
                
                if not self.is_on:
                    break
                
                self._pwm.stop()
                time.sleep(0.3)  # Silence for 300ms
            except Exception:
                break

    def close(self):
        """Clean up GPIO resources"""
        self.turn_off()
        try:
            if self._pwm:
                self._pwm.stop()
            GPIO.cleanup(self.pin)
        except Exception:
            pass
