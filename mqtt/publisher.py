"""Publish commands to MQTT topics."""

from .client import MQTTClient
from . import topics


class Publisher:
    """Publish Smart Garage commands."""

    def __init__(self, client: MQTTClient) -> None:
        self.client = client

    def publish_door_command(self, payload: str) -> None:
        self.client.publish(topics.COMMAND_DOOR, payload)

    def publish_light_command(self, payload: str) -> None:
        self.client.publish(topics.COMMAND_LIGHT, payload)
