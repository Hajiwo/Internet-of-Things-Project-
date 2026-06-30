"""Execute planner actions."""

from planner.actions import PlannerAction
from mqtt.publisher import Publisher


class Executor:
    """Send planner actions to the MQTT layer."""

    def __init__(self, publisher: Publisher) -> None:
        self.publisher = publisher

    def execute(self, actions: list[PlannerAction]) -> None:
        for action in actions:
            if action.name == "open_door":
                self.publisher.publish_door_command("open")
            elif action.name == "close_door":
                self.publisher.publish_door_command("close")
            elif action.name == "turn_on_light":
                self.publisher.publish_light_command("on")
            elif action.name == "turn_off_light":
                self.publisher.publish_light_command("off")
