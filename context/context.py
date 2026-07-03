"""Garage state context."""

from dataclasses import dataclass, field

from config.settings import settings

@dataclass(slots=True)
class Context:
    """Hold the current garage state."""
    #From sensors:
    temperature: float | None = None
    lux: float | None = None
    positions_occupied: list[bool] = field(default_factory=lambda: [False] * settings.parking_size)
    current_vehicles: dict[str, str] = field(default_factory=dict)

    #For Actuators:
    fan: bool = False
    light: bool = False
    entrance_gate: bool = False
    exit_gate: bool = False

    garage_size: int = settings.parking_size