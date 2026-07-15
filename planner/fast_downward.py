"""Fast Downward integration wrapper."""

import subprocess
import tempfile
from pathlib import Path


class FastDownward:
    """Run Fast Downward against generated Smart Garage PDDL."""

    def __init__(self, executable_path: str) -> None:
        self.executable_path = Path(executable_path)

    def build_command(
        self, domain_path: str, problem_path: str, plan_path: str | None = None
    ) -> list[str]:
        command = [str(self.executable_path)]
        if plan_path is not None:
            command.extend(["--plan-file", plan_path])
        command.extend(
            [domain_path, problem_path, "--search", "astar(lmcut())"]
        )
        return command

    def run(self, domain_path: str, problem_path: str) -> str:
        with tempfile.TemporaryDirectory(prefix="smart-garage-plan-") as directory:
            plan_path = Path(directory) / "sas_plan"
            result = subprocess.run(
                self.build_command(domain_path, problem_path, str(plan_path)),
                check=True,
                capture_output=True,
                text=True,
            )
            if plan_path.exists():
                return plan_path.read_text(encoding="utf-8")
            return result.stdout
