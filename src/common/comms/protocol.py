from dataclasses import dataclass, asdict, field
import json
import time
from enum import Enum, auto
from typing import Any

class EventType(Enum):
    ALARM_TRIGGERED = auto()
    ALARM_CLEARED = auto()
    HEARTBEAT = auto()
    SNOOZE_PRESSED = auto()
    ACK = auto()

@dataclass
class Alarm:
    """Represents an alarm with hours and minutes in 12-hour format"""
    hours: int  # 1-12
    minutes: int  # 0-59
    is_pm: bool = False  # True for PM, False for AM

    def __post_init__(self):
        """Validate alarm time"""
        if not (1 <= self.hours <= 12):
            raise ValueError(f"Hours must be 1-12 for 12-hour format, got {self.hours}")
        if not (0 <= self.minutes <= 59):
            raise ValueError(f"Minutes must be 0-59, got {self.minutes}")

    def to_dict(self) -> dict:
        return {"hours": self.hours, "minutes": self.minutes, "is_pm": self.is_pm}

    @staticmethod
    def from_dict(data: dict) -> "Alarm":
        return Alarm(
            hours=data["hours"],
            minutes=data["minutes"],
            is_pm=data.get("is_pm", False)
        )

    def get_24hr_time(self) -> tuple[int, int]:
        """Convert 12-hour format to 24-hour format. Returns (hour_24, minutes)"""
        hour_24 = self.hours % 12  # Convert 12 to 0
        if self.is_pm and self.hours != 12:
            hour_24 += 12
        elif not self.is_pm and self.hours == 12:
            hour_24 = 0
        return hour_24, self.minutes

    def get_next_trigger_time(self) -> float:
        """Calculate the next trigger time (unix timestamp) for this alarm"""
        import datetime
        now = datetime.datetime.now()
        hour_24, minute = self.get_24hr_time()
        alarm_time = now.replace(hour=hour_24, minute=minute, second=0, microsecond=0)
        
        # If the alarm time has already passed today, schedule for tomorrow
        if alarm_time <= now:
            alarm_time += datetime.timedelta(days=1)
        
        return alarm_time.timestamp()

    def __str__(self) -> str:
        """Return a human-readable string representation"""
        period = "PM" if self.is_pm else "AM"
        return f"{self.hours}:{self.minutes:02d} {period}"

@dataclass
class AlarmEvent:
    type: EventType
    data: dict[str, Any] = None
    timestamp: float | None = None
    expires_at: float | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_json(self) -> str:
        payload = asdict(self)
        payload["type"] = self.type.value
        return json.dumps(payload)

    @staticmethod
    def from_json(data: str) -> "AlarmEvent":
        raw = json.loads(data)
        raw["type"] = EventType(raw["type"])
        return AlarmEvent(**raw)
