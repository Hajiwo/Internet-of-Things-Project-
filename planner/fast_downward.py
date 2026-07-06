"""Fast Downward integration wrapper."""

import subprocess
from pathlib import Path


class FastDownward:
    """Run Fast Downward against generated Smart Garage PDDL."""

    def __init__(self, executable_path: str) -> None:
        self.executable_path = Path(executable_path)

    def build_command(self, domain_path: str, problem_path: str) -> list[str]:
        return [str(self.executable_path), domain_path, problem_path, "--search", "astar(lmcut())"]

    def run(self, domain_path: str, problem_path: str) -> str:
        result = subprocess.run(
            self.build_command(domain_path, problem_path),
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout

