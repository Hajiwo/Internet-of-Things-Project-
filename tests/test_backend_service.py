from pathlib import Path
from typing import Any

from config.settings import settings
from models.event import MQTTEvent
from planner.planner import AIPlanner
from planner.rule_backend import RulePlanningBackend
from services.camera_service import CameraRequestError
from services.backend_service import SmartGarageService


class FakeMQTTClient:
    host = "localhost"
    port = 1883
    is_connected = True

    def __init__(self) -> None:
        self.messages: list[tuple[str, Any]] = []

    def publish(self, topic: str, payload: Any) -> None:
        self.messages.append((topic, payload))


class FakeCamera:
    def read_license_plate(self) -> str:
        return "BN9123"


def test_event_updates_dashboard_state_and_publishes_command(tmp_path: Path) -> None:
    mqtt_client = FakeMQTTClient()
    planner = AIPlanner(
        backend=RulePlanningBackend(),
        domain_path=Path("planner/domain.pddl"),
        problem_path=tmp_path / "problem.pddl",
    )
    service = SmartGarageService(planner, mqtt_client=mqtt_client)  # type: ignore[arg-type]

    assert service.camera_service.sensor_factory().show_preview is False

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


def test_camera_result_enters_backend_without_publishing_camera_mqtt(
    tmp_path: Path,
) -> None:
    mqtt_client = FakeMQTTClient()
    planner = AIPlanner(
        backend=RulePlanningBackend(),
        domain_path=Path("planner/domain.pddl"),
        problem_path=tmp_path / "camera-problem.pddl",
    )
    service = SmartGarageService(planner, mqtt_client=mqtt_client)  # type: ignore[arg-type]
    service.camera_service.sensor_factory = FakeCamera  # type: ignore[assignment]

    result = service.capture_vehicle("enter")
    state = service.snapshot()

    assert result["processed"] is True
    assert state["context"]["current_vehicles"] == {
        "BN9123": result["payload"]["enter_time"]
    }
    assert state["context"]["entrance_gate"] is True
    assert mqtt_client.messages == [(settings.ACTUATOR_ENTRANCE_GATE, "open")]
    assert all(topic != settings.EVENT_VEHICLE_ENTRY for topic, _ in mqtt_client.messages)


def test_camera_api_reports_recognition_when_actuator_publish_fails(
    tmp_path: Path,
) -> None:
    class FailingMQTTClient(FakeMQTTClient):
        def publish(self, topic: str, payload: Any) -> None:
            raise RuntimeError("MQTT broker is disconnected")

    planner = AIPlanner(
        backend=RulePlanningBackend(),
        domain_path=Path("planner/domain.pddl"),
        problem_path=tmp_path / "failed-camera-problem.pddl",
    )
    service = SmartGarageService(  # type: ignore[arg-type]
        planner, mqtt_client=FailingMQTTClient()
    )
    service.camera_service.sensor_factory = FakeCamera  # type: ignore[assignment]

    try:
        service.capture_vehicle("enter")
    except CameraRequestError as error:
        assert error.status_code == 503
        assert "BN9123 was recognized" in str(error)
        assert "MQTT broker is disconnected" in str(error)
    else:
        raise AssertionError("Expected actuator publishing to fail")
