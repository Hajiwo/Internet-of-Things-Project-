"""Build PDDL problems from garage context."""

from context.context import GarageContext


class ProblemGenerator:
    """Generate planner problem text from the current context."""

    def generate(self, context: GarageContext) -> str:
        return f"""(define (problem smart-garage-problem)
  (:domain smart-garage)
  (:init
    {'(door-open)' if context.door_open else ''}
    {'(light-on)' if context.light_on else ''}
    {'(vehicle-present)' if context.vehicle_present else ''}
  )
  (:goal (and))
)"""
