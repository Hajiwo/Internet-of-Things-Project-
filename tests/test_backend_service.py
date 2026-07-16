from pathlib import Path
from typing import Any

from config.settings import settings
from models.event import MQTTEvent
from planner.planner import AIPlanner
from planner.rule_backend import RulePlanningBackend
from services.backend_service import SmartGarageService


class FakeMQTTClient:
    host = "localhost"
    port = 1883
    is_connected = True

    def __init__(self) -> None:
        self.messages: list[tuple[str, Any]] = []

    def publish(self, topic: str, payload: Any) -> None:
        self.messages.append((topic, payload))


def test_event_updates_dashboard_state_and_publishes_command(tmp_path: Path) -> None:
    mqtt_client = FakeMQTTClient()
    planner = AIPlanner(
        backend=RulePlanningBackend(),
        domain_path=Path("planner/domain.pddl"),
        problem_path=tmp_path / "problem.pddl",
    )
    service = SmartGarageService(planner, mqtt_client=mqtt_client)  # type: ignore[arg-type]

    accepted = service.process_event(
        MQTTEvent(
            settings.SENSOR_TEMPERATURE,
            {"sequence_number": 1, "temperature": 35.0},
        )
    )
    state = service.snapshot()

    assert accepted is True
    assert mqtt_client.messages == [(settings.ACTUATOR_FAN, "on")]
    assert state["context"]["temperature"] == 35.0
    assert state["context"]["fan"] is True
    assert state["last_event"]["topic"] == settings.SENSOR_TEMPERATURE
    assert state["last_command"] == {
        "time": state["last_command"]["time"],
        "topic": settings.ACTUATOR_FAN,
        "payload": "on",
    }
