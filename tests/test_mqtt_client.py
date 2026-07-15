import json
from typing import Any

import paho.mqtt.client as mqtt

from mqtt.client import MQTTClient


class FakeMessageInfo:
    rc = mqtt.MQTT_ERR_SUCCESS


def test_publish_serializes_actuator_command_as_json_string() -> None:
    client = MQTTClient()
    calls: list[tuple[str, str, int]] = []

    def fake_publish(topic: str, payload: str, qos: int) -> FakeMessageInfo:
        calls.append((topic, payload, qos))
        return FakeMessageInfo()

    client.client.publish = fake_publish  # type: ignore[method-assign]
    client.publish("garage/actuator/fan", "on")

    assert calls == [("garage/actuator/fan", json.dumps("on"), 1)]


def test_subscriber_ignores_malformed_and_non_object_payloads() -> None:
    client = MQTTClient()
    callback: Any = None
    received: list[tuple[str, dict[str, Any]]] = []

    def fake_add(topic: str, handler: Any) -> None:
        nonlocal callback
        callback = handler

    client.client.message_callback_add = fake_add  # type: ignore[method-assign]
    client.client.subscribe = lambda topic, qos: (mqtt.MQTT_ERR_SUCCESS, 1)  # type: ignore[method-assign]
    client.subscribe("garage/sensor/temperature", lambda topic, payload: received.append((topic, payload)))

    class Message:
        topic = "garage/sensor/temperature"
        payload = b"not-json"

    callback(None, None, Message())
    Message.payload = b'"on"'
    callback(None, None, Message())
    Message.payload = b'{"sequence_number": 1, "temperature": 25}'
    callback(None, None, Message())

    assert received == [
        (
            "garage/sensor/temperature",
            {"sequence_number": 1, "temperature": 25},
        )
    ]
