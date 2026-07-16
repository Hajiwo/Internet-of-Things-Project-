from typing import Any

import pytest

from config.settings import settings
from services.camera_service import CameraRequestError, CameraService


class FakePublisher:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, Any]]] = []

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        self.messages.append((topic, payload))


class FakeCamera:
    def __init__(self, plate: str = "BN9123") -> None:
        self.plate = plate

    def read_license_plate(self) -> str:
        return self.plate


def test_enter_capture_publishes_vehicle_entry_event() -> None:
    publisher = FakePublisher()
    service = CameraService(
        publisher=publisher,
        sequence_provider=lambda topic: 4,
        garage_full_provider=lambda: False,
        sensor_factory=FakeCamera,  # type: ignore[arg-type]
    )

    result = service.capture("enter")

    assert result["license_plate"] == "BN9123"
    topic, payload = publisher.messages[0]
    assert topic == settings.EVENT_VEHICLE_ENTRY
    assert payload["sequence_number"] == 4
    assert payload["license_plate"] == "BN9123"
    assert "enter_time" in payload


def test_full_garage_rejects_enter_before_starting_camera() -> None:
    started = False

    def sensor_factory() -> FakeCamera:
        nonlocal started
        started = True
        return FakeCamera()

    service = CameraService(
        publisher=FakePublisher(),
        sequence_provider=lambda topic: 1,
        garage_full_provider=lambda: True,
        sensor_factory=sensor_factory,  # type: ignore[arg-type]
    )

    with pytest.raises(CameraRequestError) as error:
        service.capture("enter")

    assert error.value.status_code == 409
    assert started is False


def test_exit_is_allowed_when_garage_is_full() -> None:
    publisher = FakePublisher()
    service = CameraService(
        publisher=publisher,
        sequence_provider=lambda topic: 2,
        garage_full_provider=lambda: True,
        sensor_factory=FakeCamera,  # type: ignore[arg-type]
    )

    service.capture("exit")

    assert publisher.messages[0][0] == settings.EVENT_VEHICLE_LEAVE
