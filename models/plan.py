"""Plan models."""

from dataclasses import dataclass, field

from planner.actions import PlannerAction


@dataclass(slots=True)
class Plan:
    """Represent an ordered list of planner actions."""

    actions: list[PlannerAction] = field(default_factory=list)
