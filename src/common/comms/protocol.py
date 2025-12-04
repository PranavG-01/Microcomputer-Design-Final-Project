from dataclasses import dataclass, asdict
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
class AlarmEvent:
    type: EventType
    data: dict[str, Any] = None
    timestamp: float | None = None

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
