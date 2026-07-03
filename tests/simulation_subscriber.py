"""Subscriber simulation for testing Smart Garage context updates."""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from broker_simulator import HOST, PORT, BrokerSimulator
from context.manager import ContextManager
from models.event import MQTTEvent
from mqtt.topics import SensorTopics


class BrokerSimulatorClient:
    """JSON-lines subscriber client for the standalone broker simulator."""

    def __init__(self, host: str = HOST, port: int = PORT) -> None:
        self.host = host
        self.port = port
        self.socket: socket.socket | None = None
        self.file = None

    def connect(self) -> None:
        self.socket = socket.create_connection((self.host, self.port))
        self.file = self.socket.makefile("r", encoding="utf-8")

    def disconnect(self) -> None:
        if self.file is not None:
            self.file.close()
        if self.socket is not None:
            self.socket.close()

    def subscribe(self, topic: str, callback: Any | None = None) -> None:
        self._send({"type": "subscribe", "topic": topic})
        if self.file is None:
            raise RuntimeError("subscriber is not connected")
        receipt = json.loads(self.file.readline())
        if receipt.get("type") == "subscribed":
            print(f"[subscriber] subscribed to {topic}")

    def listen(self, callback: Any) -> None:
        if self.file is None:
            raise RuntimeError("subscriber is not connected")
        for line in self.file:
            message = json.loads(line)
            if message.get("type") == "message":
                callback(message["topic"], message["payload"])
            elif message.get("type") == "error":
                print(f"[subscriber] broker error: {message.get('message')}")

    def _send(self, message: dict[str, Any]) -> None:
        if self.socket is None:
            raise RuntimeError("subscriber is not connected")
        self.socket.sendall(json.dumps(message).encode("utf-8") + b"\n")


class SimulationBroker:
    """Subscribe to garage topics, print messages, and update context."""

    def __init__(self, broker: BrokerSimulator | BrokerSimulatorClient | None = None) -> None:
        self.broker = broker if broker is not None else BrokerSimulatorClient()
        self.topics = SensorTopics().get_topics()
        self.context_manager = ContextManager()

        self.connect = self.broker.connect if hasattr(self.broker, "connect") else lambda: None
        self.disconnect = self.broker.disconnect if hasattr(self.broker, "disconnect") else lambda: None

    def start(self) -> None:
        """Connect and subscribe to all sensor topics."""

        self.connect()
        print(f"[subscriber] connected to broker simulator at {HOST}:{PORT}")
        print("[subscriber] subscribing topics:")
        for topic in self.topics:
            self.broker.subscribe(topic, self._on_message)

    def listen_forever(self) -> None:
        """Listen to broker messages until the user stops the process."""

        if hasattr(self.broker, "listen"):
            self.broker.listen(self._on_message)
            return

        print("[subscriber] direct in-memory mode is ready")
        while True:
            pass

    def _on_message(self, topic: str, payload: dict[str, Any]) -> None:
        """Print the incoming payload and update context."""

        print(f"\n[subscriber] received on {topic}: {payload}")
        event = MQTTEvent(topic=topic, payload=payload)
        try:
            self.context_manager.event_handler(event)
        except SystemExit:
            print("[subscriber] context manager rejected the message")
        self.context_manager.print_context()

    def stop(self) -> None:
        """Disconnect the MQTT client."""

        self.disconnect()


def main() -> None:
    subscriber = SimulationBroker()
    try:
        subscriber.start()
    except OSError as exc:
        print(f"[subscriber] cannot connect to broker at {HOST}:{PORT}: {exc}")
        print("[subscriber] start tests/broker_simulator.py first")
        return

    try:
        subscriber.listen_forever()
    except KeyboardInterrupt:
        print("\n[subscriber] stopped")
    finally:
        subscriber.stop()


if __name__ == "__main__":
    main()
