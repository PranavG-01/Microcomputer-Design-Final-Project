from dataclasses import dataclass
from datetime import datetime
from common.comms.protocol import Alarm


@dataclass
class TimeDisplay:
    """Represents a formatted time display for LCD with optional alarm info"""
    current_time: datetime
    alarm: Alarm = None
    
    def get_time_line(self) -> str:
        """Get formatted current time in 12-hour format (e.g., '2:30 PM')"""
        time_12hr = self.current_time.strftime("%I:%M %p")
        # Remove leading zero from hour (strftime %I gives 01-12)
        if time_12hr[0] == '0':
            time_12hr = time_12hr[1:]
        return time_12hr
    
    def get_alarm_line(self) -> str:
        """Get formatted alarm info (e.g., 'Alarm: 7:30 AM' or 'No Alarm')"""
        if self.alarm:
            return f"Alarm: {self.alarm}"
        else:
            return "No Alarm"
    
    def __str__(self) -> str:
        """Return both lines as a single string representation"""
        return f"{self.get_time_line()}\n{self.get_alarm_line()}"
