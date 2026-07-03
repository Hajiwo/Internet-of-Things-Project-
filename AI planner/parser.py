"""Parse planner output into actions."""

from .actions import PlannerAction


def parse_plan_output(output: str) -> list[PlannerAction]:
    """Convert planner text output into action objects."""

    actions: list[PlannerAction] = []
    for line in output.splitlines():
        line = line.strip()
        if line and not line.startswith(";"):
            actions.append(PlannerAction(name=line))
    return actions
