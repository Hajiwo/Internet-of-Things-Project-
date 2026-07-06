"""Build PDDL problems from garage context."""

from collections.abc import Iterable

from config.settings import settings
from context.context import Context


class ProblemGenerator:
    """Generate planner problem text from the current context."""

    def generate(self, context: Context) -> str:
        """Return a PDDL problem that represents desired actuator states."""

        init_predicates = self._init_predicates(context)
        goal_predicates = self._goal_predicates(context)

        init_block = self._format_predicates(init_predicates)
        goal_block = self._format_predicates(goal_predicates)

        return f"""(define (problem smart-garage-problem)
  (:domain smart-garage)
  (:init
{init_block}
  )
  (:goal (and
{goal_block}
  ))
)"""

    def _init_predicates(self, context: Context) -> list[str]:
        predicates: list[str] = []

        if self._temperature_is_high(context):
            predicates.append("temperature-high")
        if self._lux_is_dark(context):
            predicates.append("lux-dark")
        if context.fan:
            predicates.append("fan-on")
        if context.light:
            predicates.append("light-on")
        if self._garage_is_full(context):
            predicates.append("garage-full")
        if context.vehicle_waiting_to_enter:
            predicates.append("vehicle-waiting-to-enter")
        if context.vehicle_waiting_to_leave:
            predicates.append("vehicle-waiting-to-leave")
        if context.entrance_gate:
            predicates.append("entrance-gate-open")
        if context.exit_gate:
            predicates.append("exit-gate-open")

        return predicates

    def _goal_predicates(self, context: Context) -> list[str]:
        entrance_should_open = (
            context.vehicle_waiting_to_enter and not self._garage_is_full(context)
        )

        return [
            self._state_goal("fan-on", self._temperature_is_high(context)),
            self._state_goal("light-on", self._lux_is_dark(context)),
            self._state_goal("entrance-gate-open", entrance_should_open),
            self._state_goal("exit-gate-open", context.vehicle_waiting_to_leave),
        ]

    def _temperature_is_high(self, context: Context) -> bool:
        return (
            context.temperature is not None
            and context.temperature >= settings.temperature_high_threshold
        )

    def _lux_is_dark(self, context: Context) -> bool:
        return context.lux is not None and context.lux <= settings.lux_dark_threshold

    def _garage_is_full(self, context: Context) -> bool:
        return all(context.positions_occupied[: context.garage_size])

    def _state_goal(self, predicate: str, should_be_true: bool) -> str:
        if should_be_true:
            return predicate
        return f"not ({predicate})"

    def _format_predicates(self, predicates: Iterable[str]) -> str:
        return "\n".join(f"    ({predicate})" for predicate in predicates)

