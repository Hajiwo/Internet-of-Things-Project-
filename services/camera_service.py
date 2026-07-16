"""Camera API service that publishes recognized vehicle events over MQTT."""

from __future__ import annotations

from datetime import datetime
import threading
from typing import Any, Callable, Protocol

from config.settings import settings
from software_sensor.camera_sensor import CameraSensor, CameraSensorError


class CameraPublisher(Protocol):
    def publish(self, topic: str, payload: Any) -> Any:
        """Publish one camera event."""


class CameraRequestError(RuntimeError):
    """A user-facing camera request failure with an HTTP status."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class CameraService:
    """Capture a plate and publish an entry or exit event."""

    def __init__(
        self,
        publisher: CameraPublisher,
        sequence_provider: Callable[[str], int],
        garage_full_provider: Callable[[], bool],
        sensor_factory: Callable[[], CameraSensor] | None = None,
    ) -> None:
        self.publisher = publisher
        self.sequence_provider = sequence_provider
        self.garage_full_provider = garage_full_provider
        self.sensor_factory = sensor_factory or CameraSensor
        self._capture_lock = threading.Lock()
        self._published_sequences: dict[str, int] = {}

    def capture(self, direction: str) -> dict[str, Any]:
        """Run OCR and publish a contract-compatible vehicle event."""

        if direction not in {"enter", "exit"}:
            raise CameraRequestError("Direction must be 'enter' or 'exit'.", 400)
        if not self._capture_lock.acquire(blocking=False):
            raise CameraRequestError("The camera is already processing a request.", 409)
        try:
            return self._capture_locked(direction)
        finally:
            self._capture_lock.release()

    def _capture_locked(self, direction: str) -> dict[str, Any]:
        """Capture and publish while exclusive camera access is held."""

        if direction == "enter" and self.garage_full_provider():
            raise CameraRequestError(
                "The garage is full. Entry inspection is unavailable.", 409
            )

        try:
            license_plate = self.sensor_factory().read_license_plate()
        except CameraSensorError as error:
            raise CameraRequestError(str(error), 422) from error
        except (ImportError, ModuleNotFoundError) as error:
            raise CameraRequestError(
                f"Camera dependencies are unavailable: {error}", 503
            ) from error

        # Occupancy can change during the camera countdown/OCR operation.
        if direction == "enter" and self.garage_full_provider():
            raise CameraRequestError(
                "The garage became full during inspection. Entry was cancelled.", 409
            )

        topic = (
            settings.EVENT_VEHICLE_ENTRY
            if direction == "enter"
            else settings.EVENT_VEHICLE_LEAVE
        )
        payload: dict[str, Any] = {
            "sequence_number": self._next_sequence(topic),
            "license_plate": license_plate,
        }
        if direction == "enter":
            payload["enter_time"] = datetime.now().isoformat(timespec="seconds")

        self.publisher.publish(topic, payload)
        return {
            "direction": direction,
            "license_plate": license_plate,
            "topic": topic,
            "payload": payload,
        }

    def _next_sequence(self, topic: str) -> int:
        sequence = max(
            self.sequence_provider(topic),
            self._published_sequences.get(topic, 0) + 1,
        )
        self._published_sequences[topic] = sequence
        return sequence
