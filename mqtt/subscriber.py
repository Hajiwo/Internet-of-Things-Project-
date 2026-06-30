"""Receive sensor messages from MQTT topics."""

from typing import Callable

from .client import MQTTClient
from . import topics


class Subscriber:
    """Subscribe to Smart Garage sensor topics."""

    def __init__(self, client: MQTTClient) -> None:
        self.client = client

    def register_temperature_handler(self, callback: Callable) -> None:
        self.client.subscribe(topics.SENSOR_TEMPERATURE, callback)

    def register_vehicle_handler(self, callback: Callable) -> None:
        self.client.subscribe(topics.SENSOR_VEHICLE, callback)
