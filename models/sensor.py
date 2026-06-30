"""Sensor models."""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SensorReading:
    """Represent a reading from a garage sensor."""

    sensor_type: str
    value: Any
    timestamp: str | None = None
