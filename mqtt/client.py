import json
import logging
import threading
from typing import Any, Callable

import paho.mqtt.client as mqtt

from config.settings import settings

MQTTCallback = Callable[[str, dict[str, Any]], None]
logger = logging.getLogger(__name__)

class MQTTClient:
    """MQTT client for communication"""

    def __init__(self) -> None:
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.backend_client_id,
        )
        self.host = settings.mqtt_broker_addr
        self.port = settings.mqtt_broker_port
        self.keep_alive = settings.keep_alive
        self._connected = False
        self._loop_started = False

    @property
    def is_connected(self) -> bool:
        """Return whether this wrapper has an active broker connection."""

        return self._connected

    def connect(self) -> None:
        """Connect to the configured broker and start MQTT network processing."""

        result = self.client.connect(self.host, self.port, self.keep_alive)
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise ConnectionError(f"MQTT connection failed with result code {result}")
        self._connected = True
        self.client.loop_start()
        self._loop_started = True
        logger.info("Connected to MQTT broker at %s:%s", self.host, self.port)

    def disconnect(self) -> None:
        """Stop network processing and disconnect if a connection was opened."""

        if self._loop_started:
            self.client.loop_stop()
            self._loop_started = False
        if self._connected:
            self.client.disconnect()
            self._connected = False
            logger.info("Disconnected from MQTT broker")

    def publish(self, topic: str, payload: Any) -> mqtt.MQTTMessageInfo:
        """Publish a JSON-compatible value using the hardware contract."""

        message = self.client.publish(topic, json.dumps(payload), qos=1)
        if message.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(
                f"Failed to publish MQTT message on {topic}: result code {message.rc}"
            )
        return message
    
    def subscribe(self, topic: str, callback: MQTTCallback) -> None:
        """Subscribe to a JSON-object sensor/event topic."""

        def on_message(client: Any, userdata: Any, msg: mqtt.MQTTMessage) -> None:
            raw_payload = msg.payload.decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                logger.warning(
                    "Ignored malformed JSON on topic %s: %r", msg.topic, raw_payload
                )
                return

            if not isinstance(payload, dict):
                logger.warning(
                    "Ignored non-object sensor payload on topic %s: %r",
                    msg.topic,
                    payload,
                )
                return

            callback(msg.topic, payload)

        self.client.message_callback_add(topic, on_message)
        result, _message_id = self.client.subscribe(topic, qos=1)
        if result != mqtt.MQTT_ERR_SUCCESS:
            self.client.message_callback_remove(topic)
            raise RuntimeError(
                f"Failed to subscribe to MQTT topic {topic}: result code {result}"
            )
        logger.info("Subscribed to MQTT topic %s", topic)
    
    def run(self) -> None:
        """Connect and remain active until interrupted."""

        self.connect()
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.disconnect()
