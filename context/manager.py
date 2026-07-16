"""Update garage context from MQTT messages."""

import logging
import threading
from typing import Any

from config.settings import settings
from context.context import Context
from models.event import MQTTEvent

logger = logging.getLogger(__name__)


class ContextManager:
    """Apply incoming sensor data to the current garage context."""
    def __init__(self, context: Context | None = None) -> None:
        self.context = context if context is not None else Context()
        self.msg_sequences: dict[str, int] = {
            settings.SENSOR_TEMPERATURE: 0,
            settings.SENSOR_LIGHT: 0,
            settings.SENSOR_PARKING: 0,
            settings.EVENT_VEHICLE_ENTRY: 0,
            settings.EVENT_VEHICLE_LEAVE: 0,
        }
        self._lock = threading.RLock()

    def event_handler(self, event: MQTTEvent) -> bool:
        """Apply a valid, newer event and report whether context was updated."""

        with self._lock:
            return self._event_handler_locked(event)

    def _event_handler_locked(self, event: MQTTEvent) -> bool:
        """Apply an event while the context lock is held."""

        topic = event.topic
        payload = event.payload
        if topic not in self.msg_sequences:
            logger.warning("Ignored unsupported MQTT topic: %s", topic)
            return False

        sequence_number = payload.get("sequence_number")
        if isinstance(sequence_number, bool) or not isinstance(sequence_number, int):
            logger.warning("Ignored %s message with invalid sequence_number", topic)
            return False
        if sequence_number <= self.msg_sequences[topic]:
            logger.info("Ignored duplicate or older message on %s", topic)
            return False

        handlers = {
            settings.SENSOR_TEMPERATURE: self.update_temperature,
            settings.SENSOR_LIGHT: self.update_light,
            settings.SENSOR_PARKING: self.update_parking,
            settings.EVENT_VEHICLE_ENTRY: self.update_vehicle_entry,
            settings.EVENT_VEHICLE_LEAVE: self.update_vehicle_leave,
        }
        if not handlers[topic](payload):
            return False

        self.msg_sequences[topic] = sequence_number
        return True

    def next_sequence_number(self, topic: str) -> int:
        """Return the next valid sequence number for an internally published event."""

        with self._lock:
            return self.msg_sequences.get(topic, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        """Return a thread-safe, JSON-compatible copy of current context."""

        with self._lock:
            return {
                "temperature": self.context.temperature,
                "lux": self.context.lux,
                "positions_occupied": list(self.context.positions_occupied),
                "current_vehicles": dict(self.context.current_vehicles),
                "fan": self.context.fan,
                "light": self.context.light,
                "entrance_gate": self.context.entrance_gate,
                "exit_gate": self.context.exit_gate,
                "vehicle_waiting_to_enter": self.context.vehicle_waiting_to_enter,
                "vehicle_waiting_to_leave": self.context.vehicle_waiting_to_leave,
                "garage_size": self.context.garage_size,
            }

    def update_temperature(self, payload: dict[str, Any]) -> bool:
        """Update temperature from a DHT11 message."""

        temperature = payload.get("temperature")
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            logger.warning("Ignored temperature message with invalid value")
            return False
        self.context.temperature = float(temperature)
        return True

    def update_light(self, payload: dict[str, Any]) -> bool:
        """Update the provisional lux value from the A0 sensor reading."""

        lux = payload.get("lux")
        if isinstance(lux, bool) or not isinstance(lux, (int, float)):
            logger.warning("Ignored light message with invalid lux value")
            return False
        self.context.lux = float(lux)
        return True

    def update_parking(self, payload: dict[str, Any]) -> bool:
        """Update one parking position."""

        position = payload.get("position")
        on_occupy = payload.get("on_occupy")
        if (
            isinstance(position, bool)
            or not isinstance(position, int)
            or not 0 <= position < settings.parking_size
            or not isinstance(on_occupy, bool)
        ):
            logger.warning("Ignored parking message with invalid position/state")
            return False
        self.context.positions_occupied[position] = on_occupy
        return True

    def update_vehicle_entry(self, payload: dict[str, Any]) -> bool:
        """Register a vehicle waiting to enter."""

        license_plate = payload.get("license_plate") or payload.get("license")
        enter_time = payload.get("enter_time")
        if not isinstance(license_plate, str) or not license_plate.strip():
            logger.warning("Ignored vehicle-entry message without a license plate")
            return False
        if not isinstance(enter_time, str) or not enter_time.strip():
            logger.warning("Ignored vehicle-entry message without enter_time")
            return False
        self.context.current_vehicles[license_plate] = enter_time
        self.context.vehicle_waiting_to_enter = True
        return True

    def update_vehicle_leave(self, payload: dict[str, Any]) -> bool:
        """Register a vehicle waiting to leave without terminating the backend."""

        license_plate = payload.get("license_plate") or payload.get("license")
        if not isinstance(license_plate, str) or not license_plate.strip():
            logger.warning("Ignored vehicle-exit message without a license plate")
            return False
        if license_plate in self.context.current_vehicles:
            del self.context.current_vehicles[license_plate]
        else:
            logger.warning(
                "Vehicle with license plate %s was not in current vehicles",
                license_plate,
            )
        self.context.vehicle_waiting_to_leave = True
        return True

    def print_context(self) -> None:
        """Print the current context for debugging."""
        print("Current Garage Context:")
        print(f"Temperature: {self.context.temperature}")
        print(f"Lux: {self.context.lux}")
        print(f"Positions Occupied: {self.context.positions_occupied}")
        print(f"Current Vehicles: {list(self.context.current_vehicles.keys())}")
        print(f"Fan On: {self.context.fan}")
        print(f"Light On: {self.context.light}")
        print(f"Entrance Gate Open: {self.context.entrance_gate}")
        print(f"Exit Gate Open: {self.context.exit_gate}")
