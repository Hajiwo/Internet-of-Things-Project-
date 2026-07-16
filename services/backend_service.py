"""Long-running MQTT, context, planner, and actuator service."""

from __future__ import annotations

import logging
import queue
import subprocess
import threading
from collections import deque
from datetime import datetime
from typing import Any

from config.settings import settings
from context.manager import ContextManager
from executor.executor import Executor
from models.event import MQTTEvent
from mqtt.client import MQTTClient
from mqtt.eventDispatcher import MQTTEventDispatcher
from mqtt.publisher import Publisher
from mqtt.topics import SensorTopics
from planner.planner import AIPlanner
from services.camera_service import CameraRequestError, CameraService
from software_sensor.camera_sensor import CameraSensor

logger = logging.getLogger(__name__)


class SmartGarageService:
    """Own and coordinate all backend subscriber and publisher components."""

    def __init__(
        self,
        planner: AIPlanner,
        mqtt_client: MQTTClient | None = None,
        context_manager: ContextManager | None = None,
    ) -> None:
        self.mqtt_client = mqtt_client or MQTTClient()
        self.context_manager = context_manager or ContextManager()
        self.dispatcher = MQTTEventDispatcher()
        self.publisher = Publisher(self.mqtt_client)
        self.executor = Executor(self.publisher, self.context_manager.context)
        self.planner = planner
        self.camera_service = CameraService(
            sequence_provider=self.context_manager.next_sequence_number,
            garage_full_provider=self.is_garage_full,
            # OpenCV GUI calls such as imshow/waitKey are unsafe in the HTTP
            # worker thread on macOS. The web dashboard provides the UI.
            sensor_factory=lambda: CameraSensor(
                camera_index=settings.camera_index,
                countdown_seconds=settings.camera_countdown_seconds,
                capture_timeout_seconds=settings.camera_capture_timeout_seconds,
                show_preview=False,
            ),
        )
        self._events: deque[dict[str, Any]] = deque(maxlen=30)
        self._commands: deque[dict[str, Any]] = deque(maxlen=30)
        self._history_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self.last_error: str | None = None

    def start(self) -> None:
        """Connect MQTT, subscribe to inputs, and start event processing."""

        self.mqtt_client.connect()
        for topic in SensorTopics().get_topics():
            self.mqtt_client.subscribe(topic, self.dispatcher.push_event)
        self._stop_event.clear()
        self._worker = threading.Thread(
            target=self._process_events,
            name="smart-garage-events",
            daemon=True,
        )
        self._worker.start()
        logger.info("MQTT subscriber and publisher are ready")

    def stop(self) -> None:
        """Stop event processing and disconnect MQTT."""

        self._stop_event.set()
        if self._worker is not None:
            self._worker.join(timeout=2)
            self._worker = None
        self.mqtt_client.disconnect()

    def capture_vehicle(self, direction: str) -> dict[str, Any]:
        """Capture a plate and process its event directly in the backend."""

        result = self.camera_service.capture(direction)
        event = MQTTEvent(topic=result["topic"], payload=result["payload"])
        if not self.process_event(event):
            detail = self.last_error or "the camera event was rejected"
            raise CameraRequestError(
                f"License plate {result['license_plate']} was recognized, "
                f"but the backend could not complete the gate action: {detail}",
                503,
            )
        result["processed"] = True
        return result

    def is_garage_full(self) -> bool:
        snapshot = self.context_manager.snapshot()
        return all(snapshot["positions_occupied"][: snapshot["garage_size"]])

    def snapshot(self) -> dict[str, Any]:
        """Return JSON-ready state for the dashboard."""

        context = self.context_manager.snapshot()
        occupied_count = sum(context["positions_occupied"])
        with self._history_lock:
            events = list(self._events)
            commands = list(self._commands)

        return {
            "broker": {
                "connected": self.mqtt_client.is_connected,
                "address": self.mqtt_client.host,
                "port": self.mqtt_client.port,
            },
            "context": context,
            "parking": {
                "occupied": occupied_count,
                "available": context["garage_size"] - occupied_count,
                "full": occupied_count >= context["garage_size"],
            },
            "last_event": events[-1] if events else None,
            "last_command": commands[-1] if commands else None,
            "events": list(reversed(events)),
            "commands": list(reversed(commands)),
            "last_error": self.last_error,
        }

    def _process_events(self) -> None:
        while not self._stop_event.is_set():
            try:
                event = self.dispatcher.get_event(timeout=0.5)
            except queue.Empty:
                continue
            self.process_event(event)

    def process_event(self, event: MQTTEvent) -> bool:
        """Validate one event, update context, plan, and publish commands."""

        accepted = self.context_manager.event_handler(event)
        self._record_event(event, accepted)
        if not accepted:
            return False

        try:
            plan = self.planner.plan(self.context_manager.context)
            commands = self.executor.execute(plan.actions)
        except (FileNotFoundError, subprocess.CalledProcessError, RuntimeError) as error:
            self.last_error = str(error)
            logger.exception("Failed to plan or publish actuator commands")
            return False

        self.last_error = None
        for command in commands:
            self._record_command(command.topic, command.payload)
        return True

    def _record_event(self, event: MQTTEvent, accepted: bool) -> None:
        with self._history_lock:
            self._events.append(
                {
                    "time": _timestamp(),
                    "topic": event.topic,
                    "payload": event.payload,
                    "accepted": accepted,
                }
            )

    def _record_command(self, topic: str, payload: str) -> None:
        with self._history_lock:
            self._commands.append(
                {"time": _timestamp(), "topic": topic, "payload": payload}
            )


def _timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")
