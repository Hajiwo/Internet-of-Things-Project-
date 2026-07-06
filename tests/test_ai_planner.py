from pathlib import Path

from context.context import Context
from planner.actions import PlannerAction
from planner.planner import AIPlanner


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def run(self, domain_path: str, problem_path: str) -> str:
        self.calls.append((domain_path, problem_path))
        return "0: (turn-on-fan)\n1: (open-entrance-gate)\n"


def test_ai_planner_writes_problem_and_returns_plan(tmp_path: Path) -> None:
    backend = FakeBackend()
    domain_path = tmp_path / "domain.pddl"
    problem_path = tmp_path / "problem.pddl"
    domain_path.write_text("(define (domain smart-garage))", encoding="utf-8")
    context = Context(temperature=35.0, vehicle_waiting_to_enter=True)

    plan = AIPlanner(backend, domain_path, problem_path).plan(context)

    assert backend.calls == [(str(domain_path), str(problem_path))]
    assert "(temperature-high)" in problem_path.read_text(encoding="utf-8")
    assert plan.actions == [
        PlannerAction("turn-on-fan"),
        PlannerAction("open-entrance-gate"),
    ]
