import RPi.GPIO as GPIO
import time

# Global flag to ensure GPIO.setmode is called only once
_GPIO_MODE_SET = False

def _ensure_gpio_mode():
    global _GPIO_MODE_SET
    if not _GPIO_MODE_SET:
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)  # Suppress duplicate pin warnings
            _GPIO_MODE_SET = True
        except Exception:
            pass

class SnoozeButton:
    """Handles snooze button input with debouncing using RPi.GPIO."""
    
    def __init__(self, button_pin=27, hold_time=0.1):
        """
        Initialize the snooze button.
        
        Args:
            button_pin: GPIO pin number for the button
            hold_time: Time to hold button before registering (debounce), in seconds
        """
        _ensure_gpio_mode()
        self.pin = button_pin
        self.hold_time = hold_time
        self.pressed = False
        self._last_press_time = 0
        
        try:
            GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        except Exception:
            pass  # Pin may already be set up
    
    def is_pressed(self) -> bool:
        """Check if button is currently pressed (LOW on pull-up)."""
        try:
            return GPIO.input(self.pin) == GPIO.LOW
        except Exception:
            return False
    
    def wait_for_press(self, timeout=None) -> bool:
        """
        Block until button is pressed or timeout occurs.
        
        Args:
            timeout: Maximum time to wait in seconds, None for indefinite
        
        Returns:
            True if button was pressed, False if timeout occurred
        """
        start = time.time()
        while True:
            if self.is_pressed():
                # Debounce: wait for hold_time
                time.sleep(self.hold_time)
                if self.is_pressed():
                    return True
            if timeout and (time.time() - start) > timeout:
                return False
            time.sleep(0.01)
    
    def close(self):
        """Clean up GPIO resources"""
        try:
            GPIO.cleanup(self.pin)
        except Exception:
            pass
