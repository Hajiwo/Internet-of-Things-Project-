from planner.actions import PlannerAction
from planner.parser import parse_plan_output


def test_parse_fast_downward_style_plan_output() -> None:
    output = """
    0: (turn-on-light)
    1: (open-entrance-gate)
    ; cost = 2 (unit cost)
    """

    assert parse_plan_output(output) == [
        PlannerAction("turn-on-light"),
        PlannerAction("open-entrance-gate"),
    ]


def test_parse_ignores_non_action_lines() -> None:
    output = """
    Solution found.
    (turn-on-fan)
    ; cost = 1
    """

    assert parse_plan_output(output) == [PlannerAction("turn-on-fan")]

