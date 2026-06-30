"""Garage state context."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class GarageContext:
    """Hold the current garage state."""

    temperature: float | None = None
    vehicle_present: bool = False
    door_open: bool = False
    light_on: bool = False
    last_event: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
