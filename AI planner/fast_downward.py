"""Fast Downward integration wrapper."""

from pathlib import Path


class FastDownward:
    """Store planner binary configuration and execution helpers."""

    def __init__(self, executable_path: str) -> None:
        self.executable_path = Path(executable_path)

    def build_command(self, domain_path: str, problem_path: str) -> list[str]:
        return [str(self.executable_path), domain_path, problem_path]

    def run(self, domain_path: str, problem_path: str) -> str:
        raise NotImplementedError("Planner execution is not wired yet.")
