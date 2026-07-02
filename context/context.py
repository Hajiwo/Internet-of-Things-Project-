"""Garage state context."""

from dataclasses import dataclass
from ..config.settings import settings

@dataclass(slots=True)
class Context:
    """Hold the current garage state."""
    #From sensors:
    temperature: float | None = None
    lux: float | None = None
    positions_occupied: list[bool] = [False] *  settings.parking_size
    current_vehicles: dict[str, str] = {}

    #For Actuators:
    fan: bool = False
    light: bool = False
    entrance_gate: bool = False
    exit_gate: bool = False