"""Deterministic planning backend used when Fast Downward is unavailable."""

from pathlib import Path


class RulePlanningBackend:
    """Return Fast-Downward-style actions from a generated PDDL problem."""

    def run(self, domain_path: str, problem_path: str) -> str:
        problem_text = Path(problem_path).read_text(encoding="utf-8")
        init_text = _section(problem_text, ":init")
        goal_text = _section(problem_text, ":goal")
        actions: list[str] = []

        self._append_state_action(
            actions, init_text, goal_text, "fan-on", "turn-on-fan", "turn-off-fan"
        )
        self._append_state_action(
            actions,
            init_text,
            goal_text,
            "light-on",
            "turn-on-light",
            "turn-off-light",
        )
        self._append_state_action(
            actions,
            init_text,
            goal_text,
            "entrance-gate-open",
            "open-entrance-gate",
            "close-entrance-gate",
        )
        self._append_state_action(
            actions,
            init_text,
            goal_text,
            "exit-gate-open",
            "open-exit-gate",
            "close-exit-gate",
        )
        return "\n".join(f"{index}: ({action})" for index, action in enumerate(actions))

    def _append_state_action(
        self,
        actions: list[str],
        init_text: str,
        goal_text: str,
        predicate: str,
        turn_on: str,
        turn_off: str,
    ) -> None:
        currently_on = _has_positive_predicate(init_text, predicate)
        should_be_on = _has_positive_predicate(goal_text, predicate)
        should_be_off = _has_negative_predicate(goal_text, predicate)

        if should_be_on and not currently_on:
            actions.append(turn_on)
        elif should_be_off and currently_on:
            actions.append(turn_off)


def _section(text: str, marker: str) -> str:
    start = text.find(f"({marker}")
    if start == -1:
        return ""

    depth = 0
    for index in range(start, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return text[start:]


def _has_positive_predicate(section: str, predicate: str) -> bool:
    return any(line.strip() == f"({predicate})" for line in section.splitlines())


def _has_negative_predicate(section: str, predicate: str) -> bool:
    return any(
        line.strip() == f"(not ({predicate}))" for line in section.splitlines()
    )
