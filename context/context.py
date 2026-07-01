"""Garage state context."""

from dataclasses import dataclass, field
from ..config.settings import settings

@dataclass(slots=True)
class VehicleInfo:
    license_plate: str | None = None
    enter_time: str | None = None


@dataclass(slots=True)
class GarageContext:
    """Hold the current garage state."""

    #Temperature component:
    temperature: float | None = None
    fan_on: bool = False

    #Light component:
    lux: float | None = None
    light_on: bool = False

    #we have two gates: one for entance and one for exit. We can use two boolean variables to represent the state of each gate.
    #gate component:
    entrance_gate_open: bool = False
    exit_gate_open: bool = False

    #parking component:
    parking_occupied: list[bool] = field(default_factory=lambda: [False] * settings.parking_positions)
    current_vehicles: list[VehicleInfo] = field(default_factory=list)

