from config.settings import settings
from executor.executor import Executor, command_from_action
from planner.actions import PlannerAction


class FakePublisher:
    def __init__(self) -> None:
        self.client = FakeClient()

    def publish_command(self, command) -> None:
        self.client.publish(command.topic, command.payload)


class FakeClient:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def publish(self, topic: str, payload: str) -> None:
        self.messages.append((topic, payload))


def test_command_from_action_maps_planner_actions_to_actuator_topics() -> None:
    command = command_from_action(PlannerAction("open-exit-gate"))

    assert command.topic == settings.ACTUATOR_EXIT_GATE
    assert command.payload == "open"


def test_executor_publishes_commands_in_plan_order() -> None:
    publisher = FakePublisher()
    executor = Executor(publisher)  # type: ignore[arg-type]

    executor.execute(
        [
            PlannerAction("turn-on-fan"),
            PlannerAction("turn-off-light"),
            PlannerAction("close-entrance-gate"),
        ]
    )

    assert publisher.client.messages == [
        (settings.ACTUATOR_FAN, "on"),
        (settings.ACTUATOR_LIGHT, "off"),
        (settings.ACTUATOR_ENTRANCE_GATE, "close"),
    ]


def test_command_from_action_rejects_unknown_action() -> None:
    try:
        command_from_action(PlannerAction("unknown-action"))
    except ValueError:
        return

    raise AssertionError("Expected unknown planner action to raise ValueError")
