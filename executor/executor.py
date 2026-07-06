"""Execute planner actions."""

from planner.actions import PlannerAction
from models.command import Command
from mqtt.publisher import Publisher
from config.settings import settings


ACTION_COMMANDS = {
    "turn-on-fan": Command(settings.ACTUATOR_FAN, "on"),
    "turn-off-fan": Command(settings.ACTUATOR_FAN, "off"),
    "turn-on-light": Command(settings.ACTUATOR_LIGHT, "on"),
    "turn-off-light": Command(settings.ACTUATOR_LIGHT, "off"),
    "open-entrance-gate": Command(settings.ACTUATOR_ENTRANCE_GATE, "open"),
    "close-entrance-gate": Command(settings.ACTUATOR_ENTRANCE_GATE, "close"),
    "open-exit-gate": Command(settings.ACTUATOR_EXIT_GATE, "open"),
    "close-exit-gate": Command(settings.ACTUATOR_EXIT_GATE, "close"),
}


class Executor:
    """Send planner actions to the MQTT layer."""

    def __init__(self, publisher: Publisher) -> None:
        self.publisher = publisher

    def execute(self, actions: list[PlannerAction]) -> None:
        for action in actions:
            command = command_from_action(action)
            self.publisher.publish_command(command)


def command_from_action(action: PlannerAction) -> Command:
    """Translate a planner action into an actuator command."""

    try:
        return ACTION_COMMANDS[action.name]
    except KeyError as error:
        raise ValueError(f"Unsupported planner action: {action.name}") from error
