"""Publish commands to MQTT topics."""

from typing import TYPE_CHECKING

from config.settings import settings
from models.command import Command

if TYPE_CHECKING:
    from .client import MQTTClient


class Publisher:
    """Publish Smart Garage commands."""

    def __init__(self, client: "MQTTClient") -> None:
        self.client = client

    def publish_command(self, command: Command) -> None:
        self.client.publish(command.topic, command.payload)

    def publish_fan_command(self, payload: str) -> None:
        self.client.publish(settings.ACTUATOR_FAN, payload)

    def publish_light_command(self, payload: str) -> None:
        self.client.publish(settings.ACTUATOR_LIGHT, payload)

    def publish_entrance_gate_command(self, payload: str) -> None:
        self.client.publish(settings.ACTUATOR_ENTRANCE_GATE, payload)

    def publish_exit_gate_command(self, payload: str) -> None:
        self.client.publish(settings.ACTUATOR_EXIT_GATE, payload)
