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
        self.snooze_responses = set()  # Addresses that have sent snooze
        self.lock = threading.Lock()
        self.event_callback = event_callback

    def set_alarm(self, alarm: Alarm):
        """Set the alarm to be scheduled"""
        with self.lock:
            self.current_alarm = alarm
        print(f"[ALARM] Alarm scheduled for {alarm}")

    def trigger_alarm(self, alarm: Alarm):
        """Trigger an alarm and broadcast to all nodes"""
        with self.lock:
            if self.alarm_active:
                print("[ALARM] An alarm is already active, ignoring new trigger")
                return
            
            self.alarm_active = True
            self.snooze_responses.clear()
        
        print(f"[ALARM] ALARM TRIGGERED for {alarm}")
        event = AlarmEvent(
            EventType.ALARM_TRIGGERED,
            {"alarm": alarm.to_dict()},
            expires_at=alarm.get_next_trigger_time()
        )
        self.event_callback(event)

    def handle_snooze(self, addr, connected_nodes_count: int):
        """Handle a snooze event from a node"""
        print(f"[ALARM] Snooze pressed by {addr}")
        with self.lock:
            self.snooze_responses.add(addr)
            # Check if all nodes have sent snooze
            if len(self.snooze_responses) >= connected_nodes_count:
                print(f"[ALARM] All nodes have snoozed. Alarm cleared.")
                self._clear_alarm()

    def _clear_alarm(self):
        """Clear the active alarm (must be called with lock held)"""
        self.alarm_active = False
        self.snooze_responses.clear()
        
        print("[ALARM] Alarm cleared, resetting for next scheduled alarm")
        event = AlarmEvent(EventType.ALARM_CLEARED, {"reason": "all nodes snoozed"})
        self.event_callback(event)

    def is_alarm_active(self) -> bool:
        """Check if an alarm is currently active"""
        with self.lock:
            return self.alarm_active

    def get_current_alarm(self) -> Alarm:
        """Get the currently scheduled alarm"""
        with self.lock:
            return self.current_alarm
