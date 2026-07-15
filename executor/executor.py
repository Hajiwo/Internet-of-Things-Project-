"""Execute planner actions."""

from planner.actions import PlannerAction
from models.command import Command
from mqtt.publisher import Publisher
from config.settings import settings
from context.context import Context


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

    def __init__(self, publisher: Publisher, context: Context | None = None) -> None:
        self.publisher = publisher
        self.context = context

    def execute(self, actions: list[PlannerAction]) -> list[Command]:
        """Publish actions in order and apply their optimistic context effects."""

        commands: list[Command] = []
        for action in actions:
            command = command_from_action(action)
            self.publisher.publish_command(command)
            commands.append(command)
            if self.context is not None:
                apply_action_effect(self.context, action)
        return commands


def command_from_action(action: PlannerAction) -> Command:
    """Translate a planner action into an actuator command."""

    try:
        return ACTION_COMMANDS[action.name]
    except KeyError as error:
        raise ValueError(f"Unsupported planner action: {action.name}") from error


def apply_action_effect(context: Context, action: PlannerAction) -> None:
    """Apply an actuator action after it has been accepted for publishing."""

    if action.name == "turn-on-fan":
        context.fan = True
    elif action.name == "turn-off-fan":
        context.fan = False
    elif action.name == "turn-on-light":
        context.light = True
    elif action.name == "turn-off-light":
        context.light = False
    elif action.name == "open-entrance-gate":
        context.entrance_gate = True
        context.vehicle_waiting_to_enter = False
    elif action.name == "close-entrance-gate":
        context.entrance_gate = False
    elif action.name == "open-exit-gate":
        context.exit_gate = True
        context.vehicle_waiting_to_leave = False
    elif action.name == "close-exit-gate":
        context.exit_gate = False
    else:
        raise ValueError(f"Unsupported planner action: {action.name}")
