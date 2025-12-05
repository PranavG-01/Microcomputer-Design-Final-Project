from common.comms.node_client import AlarmNode
from common.comms.protocol import AlarmEvent, EventType, Alarm
from common.io.button import SnoozeButton
from common.io.led import LedController
import time
import threading

node = None
button = None
led = None

def handle_events():
    """Handle incoming events from the host"""
    buffer = ""
    while node and node.connected:
        try:
            data = node.socket.recv(4096).decode()
            if not data:
                break
            buffer += data
            
            # Messages separated by newline
            while "\n" in buffer:
                packet, buffer = buffer.split("\n", 1)
                event = AlarmEvent.from_json(packet)
                print(f"[NODE] Received: {event.type.name}")
                
                if event.type == EventType.ALARM_SET:
                    # Alarm scheduled: steady LED on
                    print("[NODE] Alarm set received")
                    try:
                        if led:
                            led.on()
                        else:
                            print("[NODE] LED not initialized")
                    except Exception as e:
                        print(f"[NODE] Failed to turn on LED: {e}")
                elif event.type == EventType.ALARM_TRIGGERED:
                    node.alarm_triggered = True
                    print("[NODE] ALARM TRIGGERED!")
                    # Start blinking LED
                    try:
                        if led:
                            led.blink()
                    except Exception as e:
                        print(f"[NODE] Failed to blink LED: {e}")
                elif event.type == EventType.ALARM_CLEARED:
                    node.alarm_triggered = False
                    print("[NODE] Alarm cleared")
                    # Turn off LED
                    try:
                        if led:
                            led.off()
                    except Exception:
                        pass
        except Exception as e:
            print(f"[NODE] Error receiving events: {e}")
            break


def button_monitor():
    """Monitor button presses while alarm is triggered"""
    while node:
        try:
            if node.is_alarm_triggered() and button:
                if button.is_pressed():
                    print("[NODE] Snooze button pressed!")
                    # Send snooze event to host
                    snooze_event = AlarmEvent(EventType.SNOOZE_PRESSED, {"node": "client"})
                    node.send(snooze_event)
                    # Debounce: wait for release
                    time.sleep(0.5)
            time.sleep(0.05)  # Poll every 50ms
        except Exception as e:
            print(f"[NODE] Error in button monitor: {e}")
            time.sleep(0.05)


def main():
    global node, button, led
    node = AlarmNode()
    node.start_discovery()  # Zeroconf discovery

    print("[NODE APP] Waiting for host...")

    # Wait until the node connects
    while not node.connected:
        time.sleep(0.2)

    print("[NODE APP] Connected to host!")

    # Send a heartbeat to host
    hb = AlarmEvent(EventType.HEARTBEAT, {"node_id": "demo"})
    node.send(hb)

    # Initialize button
    try:
        button = SnoozeButton(button_pin=23)
        print("[NODE APP] Button initialized")
    except Exception as e:
        print(f"[NODE APP] Failed to initialize button: {e}")

    # Initialize LED
    try:
        led = LedController(pin=24)
        print(f"[NODE APP] LED initialized")
    except Exception as e:
        print(f"[NODE APP] Failed to initialize LED: {e}")
        led = None

    # Start event handler thread
    event_thread = threading.Thread(target=handle_events, daemon=True)
    event_thread.start()

    # Start button monitor thread
    button_thread = threading.Thread(target=button_monitor, daemon=True)
    button_thread.start()

    try:
        while True:
            time.sleep(10)

            # Send a heartbeat
            hb = AlarmEvent(EventType.HEARTBEAT)
            node.send(hb)

    except KeyboardInterrupt:
        print("[NODE APP] Shutting down")
        if button:
            button.close()
        if led:
            led.close()
        node.stop()

if __name__ == "__main__":
    main()
