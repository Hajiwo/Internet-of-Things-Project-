"""Manual MQTT connection test for the Smart Garage backend."""

import time
from typing import Any

from config.settings import settings
from mqtt.client import MQTTClient
from mqtt.topics import ActuatorTopics, SensorTopics


# Normal application entry point (temporarily disabled while testing hardware):
#
# from context.manager import ContextManager
# from mqtt.eventDispatcher import MQTTEventDispatcher
#
# def main() -> None:
#     """Run the complete backend application."""
#     print("Backend now starts running")
#     mqtt_client = MQTTClient()
#     event_dispatcher = MQTTEventDispatcher()
#     context_manager = ContextManager()
#
#     mqtt_client.connect()
#     for sensor_topic in SensorTopics().get_topics():
#         mqtt_client.subscribe(sensor_topic, event_dispatcher.push_event)
#
#     while True:
#         event = event_dispatcher.get_event()
#         context_manager.event_handler(event)


def test_connecting() -> None:
    """Receive Raspberry Pi sensor data and periodically test an actuator topic."""
    mqtt_client = MQTTClient()

    def show_received_message(topic: str, payload: dict[str, Any]) -> None:
        """Print every sensor message received from the Raspberry Pi."""
        print(f"[RECEIVED] topic={topic}, payload={payload}", flush=True)

    print(
        f"Detecting MQTT broker at {settings.mqtt_broker_addr}:"
        f"{settings.mqtt_broker_port} ...",
        flush=True,
    )

    try:
        # connect() raises an exception when the broker cannot be reached.
        mqtt_client.connect()
        print("[CONNECTED] MQTT broker detected.", flush=True)

        # Listen to every topic on which the Raspberry Pi publishes sensor data.
        for topic in SensorTopics().get_topics():
            mqtt_client.subscribe(topic, show_received_message)
            print(f"[SUBSCRIBED] {topic}", flush=True)

        # Use a real actuator command so it is easy to verify on the Raspberry Pi.
        test_topic = ActuatorTopics().ACTUATOR_FAN
        sequence_number = 1
        print("Press Ctrl+C to stop the test.", flush=True)

        while True:
            payload = {
                "command": "on",
                "test": True,
                "sequence_number": sequence_number,
            }
            mqtt_client.publish(test_topic, payload)
            print(f"[PUBLISHED] topic={test_topic}, payload={payload}", flush=True)
            sequence_number += 1
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nMQTT hardware test stopped.", flush=True)
    except (ConnectionError, OSError) as error:
        print(f"[CONNECTION FAILED] {error}", flush=True)
    finally:
        # disconnect() is harmless after a successful connection and lets queued
        # QoS 1 traffic finish cleanly before this program exits.
        try:
            mqtt_client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    test_connecting()
