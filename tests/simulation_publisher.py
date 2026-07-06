"""Interactive Raspberry Pi publisher simulator for Smart Garage messages."""

from __future__ import annotations

import json
import socket
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mqtt.topics import SensorTopics
from tests.broker_simulator import HOST, PORT, BrokerSimulator


class BrokerSimulatorClient:
    """Small JSON-lines client for the standalone broker simulator."""

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

    def publish(self, topic: str, payload: Any) -> dict[str, Any]:
        if self.socket is None or self.file is None:
            raise RuntimeError("publisher is not connected")
        self._send({"type": "publish", "topic": topic, "payload": payload})
        return json.loads(self.file.readline())

    def _send(self, message: dict[str, Any]) -> None:
        if self.socket is None:
            raise RuntimeError("publisher is not connected")
        self.socket.sendall(json.dumps(message).encode("utf-8") + b"\n")


class SimulationPublisher:
    """Publish Smart Garage sensor messages through a simulator broker."""

    def __init__(self, broker: BrokerSimulator | BrokerSimulatorClient | None = None) -> None:
        self.broker = broker if broker is not None else BrokerSimulatorClient()
        self.topics = SensorTopics()
        self.sequences: dict[str, int] = defaultdict(int)

        self.connect = self.broker.connect if hasattr(self.broker, "connect") else lambda: None
        self.disconnect = self.broker.disconnect if hasattr(self.broker, "disconnect") else lambda: None

    def start(self) -> None:
        self.connect()

    def stop(self) -> None:
        self.disconnect()

    def next_sequence(self, topic: str) -> int:
        self.sequences[topic] += 1
        return self.sequences[topic]

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        payload.setdefault("sequence_number", self.next_sequence(topic))
        print(f"[publisher] sending to {topic}: {payload}")
        receipt = self.broker.publish(topic, payload)
        if isinstance(receipt, dict) and "subscribers" in receipt:
            print(f"[publisher] broker delivered to {receipt['subscribers']} subscriber(s)")

    def publish_temperature(self) -> None:
        temperature = read_float("Temperature value: ")
        self.publish(self.topics.SENSOR_TEMPERATURE, {"temperature": temperature})

    def publish_light(self) -> None:
        lux = read_float("Light lux value: ")
        self.publish(self.topics.SENSOR_LIGHT, {"lux": lux})

    def publish_parking(self) -> None:
        position = read_int("Parking position (0-3): ")
        occupied = read_bool("Occupied? (y/n): ")
        self.publish(self.topics.PARKING, {"position": position, "on_occupy": occupied})

    def publish_vehicle_entry(self) -> None:
        license_plate = input("License plate entering: ").strip() or "BN9123"
        enter_time = datetime.now().isoformat(timespec="seconds")
        self.publish(
            self.topics.VEHICLE_ENTRY,
            {"license_plate": license_plate, "enter_time": enter_time},
        )

    def publish_vehicle_leave(self) -> None:
        license_plate = input("License plate leaving: ").strip() or "BN9123"
        self.publish(self.topics.VEHICLE_LEAVE, {"license_plate": license_plate})

    def publish_demo_messages(self) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        self.publish(self.topics.SENSOR_TEMPERATURE, {"temperature": 28.5})
        self.publish(self.topics.SENSOR_LIGHT, {"lux": 320})
        self.publish(self.topics.PARKING, {"position": 2, "on_occupy": True})
        self.publish(self.topics.VEHICLE_ENTRY, {"license_plate": "BN9123", "enter_time": now})
        self.publish(self.topics.VEHICLE_LEAVE, {"license_plate": "BN9123"})


def read_float(prompt: str) -> float:
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Please enter a number.")


def read_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Please enter an integer.")


def read_bool(prompt: str) -> bool:
    while True:
        value = input(prompt).strip().lower()
        if value in {"y", "yes", "true", "1"}:
            return True
        if value in {"n", "no", "false", "0"}:
            return False
        print("Please enter y or n.")


def print_menu() -> None:
    print("\nChoose a message to publish:")
    print("  1. temperature")
    print("  2. vehicle entry")
    print("  3. vehicle leave")
    print("  4. light")
    print("  5. parking occupancy")
    print("  6. demo messages")
    print("  q. quit")


def main() -> None:
    publisher = SimulationPublisher()
    try:
        publisher.start()
    except OSError as exc:
        print(f"[publisher] cannot connect to broker at {HOST}:{PORT}: {exc}")
        print("[publisher] start tests/broker_simulator.py first")
        return

    print(f"[publisher] connected to broker simulator at {HOST}:{PORT}")
    try:
        while True:
            print_menu()
            choice = input("> ").strip().lower()
            if choice == "1":
                publisher.publish_temperature()
            elif choice == "2":
                publisher.publish_vehicle_entry()
            elif choice == "3":
                publisher.publish_vehicle_leave()
            elif choice == "4":
                publisher.publish_light()
            elif choice == "5":
                publisher.publish_parking()
            elif choice == "6":
                publisher.publish_demo_messages()
            elif choice in {"q", "quit", "exit"}:
                break
            else:
                print("Unknown choice.")
    except KeyboardInterrupt:
        print("\n[publisher] stopped")
    finally:
        publisher.stop()


if __name__ == "__main__":
    main()
