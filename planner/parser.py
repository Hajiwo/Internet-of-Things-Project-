"""Parse planner output into actions."""

import re

from .actions import AVAILABLE_ACTIONS, PlannerAction

_ACTION_RE = re.compile(r"^\s*(?:\d+:\s*)?\((?P<body>[^)]+)\)")


def parse_plan_output(output: str) -> list[PlannerAction]:
    """Convert Fast Downward plan text into action objects."""

    actions: list[PlannerAction] = []
    for line in output.splitlines():
        parsed = _parse_plan_line(line)
        if parsed is not None:
            actions.append(parsed)
    return actions


def _parse_plan_line(line: str) -> PlannerAction | None:
    line = line.strip()
    if not line or line.startswith(";"):
        return None

    match = _ACTION_RE.match(line)
    if not match:
        return None

    tokens = match.group("body").lower().split()
    if not tokens or tokens[0] not in AVAILABLE_ACTIONS:
        return None

    return PlannerAction(name=tokens[0], parameters=tuple(tokens[1:]))

