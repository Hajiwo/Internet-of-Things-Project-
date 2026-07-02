"""Simulation subscriber that prints received MQTT messages and the updated garage context."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from context.manager import ContextManager
from models.event import MQTTEvent
from mqtt.client import MQTTClient
from mqtt.topics import SensorTopics
from broker_simulator import BrokerSimulator


class SimulationBroker:
    """Subscribe to garage topics, print messages, and update the context."""

    def __init__(self, broker: BrokerSimulator) -> None:
        self.broker = broker
        self.client = MQTTClient()
        self.topics = SensorTopics().get_topics()
        self.context_manager = ContextManager()

        self.client.connect = lambda: None
        self.client.disconnect = lambda: None
        self.client.subscribe = self.broker.subscribe
        self.client.publish = self.broker.publish

    def start(self) -> None:
        """Connect and subscribe to all sensor topics."""
        self.client.connect()
        for topic in self.topics:
            self.client.subscribe(topic, self._on_message)
        print(f"[broker] connected to {settings.mqtt_broker_addr}:{settings.mqtt_broker_port} (simulated)")
        print("[broker] subscribed topics:")
        for topic in self.topics:
            print(f"  - {topic}")

    def _on_message(self, topic: str, payload: dict[str, Any]) -> None:
        """Print the incoming payload and update context."""
        print(f"\n[broker] received on {topic}: {payload}")
        event = MQTTEvent(topic=topic, payload=payload)
        self.context_manager.event_handler(event)
        self.context_manager.print_context()

    def stop(self) -> None:
        """Disconnect the MQTT client."""
        self.client.disconnect()


def main() -> None:
    broker = BrokerSimulator()
    subscriber = SimulationBroker(broker)
    subscriber.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        subscriber.stop()
        print("[broker] stopped")


if __name__ == "__main__":
    main()
