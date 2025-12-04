import RPi.GPIO as GPIO
import threading
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

class LedController:
    """Simple LED controller with steady on/off and blink support using RPi.GPIO."""

    def __init__(self, pin):
        _ensure_gpio_mode()
        try:
            GPIO.setup(pin, GPIO.OUT)
        except Exception:
            pass  # Pin may already be set up
        self.pin = pin
        self._blinking = False
        self._blink_thread = None

    def on(self):
        self.stop_blink()
        try:
            GPIO.output(self.pin, GPIO.HIGH)
        except Exception:
            pass

    def off(self):
        self.stop_blink()
        try:
            GPIO.output(self.pin, GPIO.LOW)
        except Exception:
            pass

    def blink(self, on_time=0.5, off_time=0.5):
        """Start blinking in a background thread."""
        self.stop_blink()
        self._blinking = True

        def _blink_loop():
            while self._blinking:
                try:
                    GPIO.output(self.pin, GPIO.HIGH)
                except Exception:
                    pass
                time.sleep(on_time)
                if not self._blinking:
                    break
                try:
                    GPIO.output(self.pin, GPIO.LOW)
                except Exception:
                    pass
                time.sleep(off_time)
            # Ensure LED off when stopping blink
            try:
                GPIO.output(self.pin, GPIO.LOW)
            except Exception:
                pass

        self._blink_thread = threading.Thread(target=_blink_loop, daemon=True)
        self._blink_thread.start()

    def stop_blink(self):
        if self._blinking:
            self._blinking = False
            if self._blink_thread:
                self._blink_thread.join(timeout=0.2)
                self._blink_thread = None

    def close(self):
        self.stop_blink()
        try:
            GPIO.output(self.pin, GPIO.LOW)
        except Exception:
            pass
        try:
            GPIO.cleanup(self.pin)
        except Exception:
            pass
