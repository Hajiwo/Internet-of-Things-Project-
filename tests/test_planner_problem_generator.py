from context.context import Context
from planner.problem_generator import ProblemGenerator


def test_generate_problem_for_hot_dark_entry_context() -> None:
    context = Context(
        temperature=34.0,
        lux=50.0,
        positions_occupied=[True, False, False],
        vehicle_waiting_to_enter=True,
    )

    problem = ProblemGenerator().generate(context)

    assert "(temperature-high)" in problem
    assert "(lux-dark)" in problem
    assert "(vehicle-waiting-to-enter)" in problem
    assert "(garage-full)" not in problem
    assert "(fan-on)" in problem
    assert "(light-on)" in problem
    assert "(entrance-gate-open)" in problem
    assert "(not (exit-gate-open))" in problem


def test_generate_problem_closes_idle_actuators() -> None:
    context = Context(
        temperature=20.0,
        lux=250.0,
        fan=True,
        light=True,
        entrance_gate=True,
        exit_gate=True,
    )

    problem = ProblemGenerator().generate(context)

    assert "(fan-on)" in problem
    assert "(light-on)" in problem
    assert "(entrance-gate-open)" in problem
    assert "(exit-gate-open)" in problem
    assert "(not (fan-on))" in problem
    assert "(not (light-on))" in problem
    assert "(not (entrance-gate-open))" in problem
    assert "(not (exit-gate-open))" in problem

