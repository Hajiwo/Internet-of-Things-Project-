"""Simulate the Raspberry Pi broker, sensors, and actuators locally."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Any

from config.settings import settings
from mqtt.simulation_client import SimulationMQTTClient
from mqtt.topics import ActuatorTopics, SensorTopics
from simulator.broker import BrokerTCPServer

logger = logging.getLogger("rp-simulator")


class RaspberryPiSimulator:
    """Run a local broker and mimic Raspberry Pi hardware behavior."""

    def __init__(self) -> None:
        self.host = settings.simulator_host
        self.port = settings.simulator_port
        self.interval = settings.simulator_sensor_interval
        self.broker = BrokerTCPServer((self.host, self.port))
        self.client = SimulationMQTTClient(self.host, self.port)
        self.sensor_topics = SensorTopics()
        self.actuator_topics = ActuatorTopics()
        self.sequences: dict[str, int] = defaultdict(int)
        self.temperature = 25.0
        self.lux = 300.0
        self.parking = [False] * settings.parking_size
        self.actuators = {
            "fan": "off",
            "light": "off",
            "entrance": "close",
            "exit": "close",
        }
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._broker_thread: threading.Thread | None = None
        self._sensor_thread: threading.Thread | None = None

    def start(self) -> None:
        self._broker_thread = threading.Thread(
            target=self.broker.serve_forever,
            name="rp-simulator-broker",
            daemon=True,
        )
        self._broker_thread.start()
        self.client.connect()
        for topic in self.actuator_topics.get_topics():
            self.client.subscribe(topic, self._receive_actuator_command)
        self._sensor_thread = threading.Thread(
            target=self._publish_sensor_loop,
            name="rp-simulator-sensors",
            daemon=True,
        )
        self._sensor_thread.start()
        logger.info("Raspberry Pi simulator running at %s:%s", self.host, self.port)

    def stop(self) -> None:
        self._stop_event.set()
        self.client.disconnect()
        self.broker.shutdown()
        self.broker.server_close()
        if self._sensor_thread is not None:
            self._sensor_thread.join(timeout=2)
        if self._broker_thread is not None:
            self._broker_thread.join(timeout=2)

    def run_console(self) -> None:
        self._print_help()
        while not self._stop_event.is_set():
            try:
                command = input("rp> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if command in {"q", "quit", "exit"}:
                break
            if command in {"h", "help", "?"}:
                self._print_help()
            elif command in {"s", "status"}:
                self._print_state()
            elif command in {"t", "temperature"}:
                self.temperature = self._read_float("Temperature: ")
                self._publish_all_sensors()
            elif command in {"l", "light"}:
                self.lux = self._read_float("Light reading: ")
                self._publish_all_sensors()
            elif command in {"p", "parking"}:
                position = self._read_position()
                with self._state_lock:
                    self.parking[position] = not self.parking[position]
                self._publish_all_sensors()
            elif command == "hot-dark":
                self.temperature = 35.0
                self.lux = 20.0
                self._publish_all_sensors()
            elif command == "normal":
                self.temperature = 25.0
                self.lux = 300.0
                self._publish_all_sensors()
            elif command:
                print("Unknown command. Type 'help'.")

    def _publish_sensor_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._publish_all_sensors()
            except RuntimeError as error:
                if not self._stop_event.is_set():
                    logger.error("Sensor publishing failed: %s", error)
            self._stop_event.wait(self.interval)

    def _publish_all_sensors(self) -> None:
        with self._state_lock:
            temperature = self.temperature
            lux = self.lux
            parking = list(self.parking)
        self._publish(
            self.sensor_topics.SENSOR_TEMPERATURE,
            {"temperature": temperature},
        )
        self._publish(self.sensor_topics.SENSOR_LIGHT, {"lux": lux})
        for position, occupied in enumerate(parking):
            self._publish(
                self.sensor_topics.SENSOR_PARKING,
                {"position": position, "on_occupy": occupied},
            )

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        self.sequences[topic] += 1
        message = {"sequence_number": self.sequences[topic], **payload}
        self.client.publish(topic, message)

    def _receive_actuator_command(self, topic: str, payload: Any) -> None:
        mapping = {
            self.actuator_topics.ACTUATOR_FAN: "fan",
            self.actuator_topics.ACTUATOR_LIGHT: "light",
            self.actuator_topics.ACTUATOR_ENTRANCE_GATE: "entrance",
            self.actuator_topics.ACTUATOR_EXIT_GATE: "exit",
        }
        actuator = mapping.get(topic, topic)
        with self._state_lock:
            self.actuators[actuator] = str(payload)
        print(f"\n[ACTUATOR] {actuator.upper()} <- {payload!r}")
        print("rp> ", end="", flush=True)

    def _print_state(self) -> None:
        with self._state_lock:
            print(f"Temperature: {self.temperature:.1f} °C")
            print(f"Light:       {self.lux:.1f}")
            print(f"Parking:     {self.parking}")
            print(f"Actuators:   {self.actuators}")

    def _print_help(self) -> None:
        print(
            "\nCommands:\n"
            "  temperature (t)  Set temperature\n"
            "  light (l)        Set light reading\n"
            "  parking (p)      Toggle parking position 0-2\n"
            "  hot-dark          Set 35 °C and light 20\n"
            "  normal            Set 25 °C and light 300\n"
            "  status (s)       Show simulated hardware state\n"
            "  help (h)         Show commands\n"
            "  quit (q)         Stop simulator\n"
        )

    def _read_float(self, prompt: str) -> float:
        while True:
            try:
                return float(input(prompt))
            except ValueError:
                print("Please enter a number.")

    def _read_position(self) -> int:
        while True:
            try:
                position = int(input("Parking position (0-2): "))
            except ValueError:
                print("Please enter an integer.")
                continue
            if 0 <= position < settings.parking_size:
                return position
            print("Position must be between 0 and 2.")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    simulator = RaspberryPiSimulator()
    try:
        simulator.start()
        simulator.run_console()
    finally:
        simulator.stop()
        logger.info("Raspberry Pi simulator stopped")


if __name__ == "__main__":
    main()
