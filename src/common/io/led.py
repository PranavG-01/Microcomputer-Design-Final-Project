import RPi.GPIO as GPIO
import threading
import time

class LedController:
    """Simple LED controller with steady on/off and blink support."""

    def __init__(self, pin):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
        self.pin = pin
        self._blinking = False
        self._blink_thread = None

    def on(self):
        self.stop_blink()
        GPIO.output(self.pin, True)
        print("led on")

    def off(self):
        self.stop_blink()
        GPIO.output(self.pin, False)

    def blink(self, on_time=0.5, off_time=0.5):
        """Start blinking in a background thread."""
        # If already blinking, adjust times by restarting
        self.stop_blink()
        self._blinking = True

        def _blink_loop():
            while self._blinking:
                self.led.on()
                time.sleep(on_time)
                if not self._blinking:
                    break
                self.led.off()
                time.sleep(off_time)
            # ensure LED off when stopping blink
            try:
                self.led.off()
            except Exception:
                pass

        self._blink_thread = threading.Thread(target=_blink_loop, daemon=True)
        self._blink_thread.start()

    def stop_blink(self):
        if self._blinking:
            self._blinking = False
            # thread will exit soon
            if self._blink_thread:
                self._blink_thread.join(timeout=0.2)
                self._blink_thread = None

    def close(self):
        self.stop_blink()
        try:
            self.led.off()
        except Exception:
            pass
        try:
            GPIO.cleanup(self.pin)
        except Exception:
            pass
