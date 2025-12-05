import threading
from common.comms.protocol import Alarm, AlarmEvent, EventType


class AlarmManager:
    """Manages alarm state and handles alarm-related events"""
    
    def __init__(self, event_callback):
        """
        Initialize the alarm manager.
        
        Args:
            event_callback: Function to call when broadcasting events.
                           Takes (event: AlarmEvent) as argument.
        """
        self.current_alarm = None  # Single Alarm object scheduled
        self.alarm_active = False  # Is an alarm currently triggered?
        self.snooze_count = 0      # Number of devices that have snoozed
        self.lock = threading.Lock()
        self.event_callback = event_callback

    def set_alarm(self, alarm: Alarm):
        """Set the alarm to be scheduled"""
        with self.lock:
            self.current_alarm = alarm
            self.alarm_active = False
            self.snooze_count = 0
        print(f"[ALARM] Alarm set for {alarm}")
        # Broadcast alarm set to nodes so they can update indicators
        event = AlarmEvent(EventType.ALARM_SET, {"alarm": alarm.to_dict()})
        self.event_callback(event)

    def remove_alarm(self):
        """Remove the currently scheduled alarm"""
        with self.lock:
            self.current_alarm = None
            self.alarm_active = False
            self.snooze_count = 0
        print("[ALARM] Alarm removed")
        event = AlarmEvent(EventType.ALARM_CLEARED, {})
        self.event_callback(event)

    def trigger_alarm(self, alarm: Alarm):
        """Trigger an alarm and broadcast to all nodes"""
        with self.lock:
            if self.alarm_active:
                print("[ALARM] Alarm already active, ignoring trigger")
                return
            self.alarm_active = True
            self.snooze_count = 0
        
        print(f"[ALARM] ALARM TRIGGERED for {alarm}")
        event = AlarmEvent(EventType.ALARM_TRIGGERED, {"alarm": alarm.to_dict()})
        self.event_callback(event)

    def handle_snooze(self, connected_nodes_count: int, source="node"):
        """Handle snooze from either node or host"""
        with self.lock:
            if not self.alarm_active:
                return

            self.snooze_count += 1
            total_devices = connected_nodes_count + 1  # host + nodes

            print(f"[ALARM] Snooze from {source}. "
                f"{self.snooze_count}/{total_devices} devices snoozed.")

            if self.snooze_count >= total_devices:
                print(f"[ALARM] All {total_devices} devices snoozed. Clearing alarm.")
                self.alarm_active = False
                self.current_alarm = None
                self.snooze_count = 0
                event = AlarmEvent(EventType.ALARM_CLEARED, {})
                self.event_callback(event)

    def is_alarm_active(self) -> bool:
        """Check if an alarm is currently active"""
        with self.lock:
            return self.alarm_active

    def get_current_alarm(self) -> Alarm:
        """Get the currently scheduled alarm"""
        with self.lock:
            return self.current_alarm
