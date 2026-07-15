"""Plan garage actions from the current context."""

from pathlib import Path
from typing import Protocol

from context.context import Context
from models.plan import Plan

from .parser import parse_plan_output
from .problem_generator import ProblemGenerator


class PlannerBackend(Protocol):
    """Planner backend capable of running domain and problem files."""

    def run(self, domain_path: str, problem_path: str) -> str:
        """Run the planner and return textual planner output."""


class AIPlanner:
    """Generate a PDDL problem and parse the backend plan output."""

    def __init__(
        self,
        backend: PlannerBackend,
        domain_path: str | Path,
        problem_path: str | Path = "problem.pddl",
        problem_generator: ProblemGenerator | None = None,
    ) -> None:
        self.backend = backend
        self.domain_path = Path(domain_path)
        self.problem_path = Path(problem_path)
        self.problem_generator = problem_generator or ProblemGenerator()

    def plan(self, context: Context) -> Plan:
        """Create a PDDL problem file, run the backend, and return a plan."""

        problem_text = self.problem_generator.generate(context)
        self.problem_path.parent.mkdir(parents=True, exist_ok=True)
        self.problem_path.write_text(problem_text, encoding="utf-8")

        output = self.backend.run(str(self.domain_path), str(self.problem_path))
        return Plan(actions=parse_plan_output(output))
