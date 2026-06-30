"""Thin wrapper around paho-mqtt."""

from dataclasses import dataclass
from typing import Callable

import paho.mqtt.client as mqtt


@dataclass
class MQTTClient:
    """Encapsulate MQTT client setup and lifecycle."""

    host: str
    port: int
    username: str = ""
    password: str = ""

    def __post_init__(self) -> None:
        self.client = mqtt.Client()
        if self.username:
            self.client.username_pw_set(self.username, self.password)

    def connect(self) -> None:
        self.client.connect(self.host, self.port)

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> None:
        self.client.publish(topic, payload, qos=qos, retain=retain)

    def subscribe(self, topic: str, callback: Callable) -> None:
        self.client.subscribe(topic)
        self.client.message_callback_add(topic, callback)

    def loop_start(self) -> None:
        self.client.loop_start()

    def loop_stop(self) -> None:
        self.client.loop_stop()
