"""Event models."""

from dataclasses import dataclass
from typing import Any

@dataclass(slots=True, frozen=True)
class MQTTEvent:
    """Represent an event received from an MQTT topic."""
    topic: str
    payload: dict[str, Any]
