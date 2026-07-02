"""Simulation publisher that sends sample garage MQTT messages."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mqtt.client import MQTTClient
from mqtt.topics import SensorTopics


class SimulationPublisher:
    """Publish a small sequence of sample messages for testing."""

    def __init__(self) -> None:
        self.client = MQTTClient()
        self.topics = SensorTopics()

    def start(self) -> None:
        self.client.connect()

    def stop(self) -> None:
        self.client.disconnect()

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        print(f"[publisher] sending to {topic}: {payload}")
        self.client.publish(topic, payload)

    def publish_demo_messages(self) -> None:
        self.start()
        now = datetime.now().isoformat(timespec="seconds")
        self.publish(self.topics.SENSOR_TEMPERATURE, {"sequence_number": 1, "temperature": 28.5})
        self.publish(self.topics.SENSOR_LIGHT, {"sequence_number": 1, "lux": 320})
        self.publish(
            self.topics.PARKING,
            {"sequence_number": 1, "position": 2, "on_occupy": True},
        )
        self.publish(
            self.topics.VEHICLE_ENTRY,
            {"sequence_number": 1, "license_plate": "BN9123", "enter_time": now},
        )
        self.publish(
            self.topics.VEHICLE_LEAVE,
            {"sequence_number": 1, "license_plate": "BN9123"},
        )


def main() -> None:
    publisher = SimulationPublisher()
    try:
        publisher.publish_demo_messages()
    finally:
        publisher.stop()


if __name__ == "__main__":
    main()
