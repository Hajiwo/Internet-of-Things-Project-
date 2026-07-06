"""Planner action definitions."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlannerAction:
    """Represent a planner action by name and parameters."""

    name: str
    parameters: tuple[str, ...] = ()


AVAILABLE_ACTIONS = frozenset(
    {
        "turn-on-fan",
        "turn-off-fan",
        "turn-on-light",
        "turn-off-light",
        "open-entrance-gate",
        "close-entrance-gate",
        "open-exit-gate",
        "close-exit-gate",
    }
)

