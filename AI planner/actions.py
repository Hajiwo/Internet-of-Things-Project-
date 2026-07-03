"""Planner action definitions."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlannerAction:
    """Represent a planner action by name and parameters."""

    name: str
    parameters: tuple[str, ...] = ()


AVAILABLE_ACTIONS = (
    "open_door",
    "close_door",
    "turn_on_light",
    "turn_off_light",
)
