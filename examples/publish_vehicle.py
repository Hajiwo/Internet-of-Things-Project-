"""Example script for publishing vehicle presence."""

from mqtt.client import MQTTClient
from mqtt.publisher import Publisher
from config.settings import settings


def main() -> None:
    client = MQTTClient(settings.mqtt_host, settings.mqtt_port, settings.mqtt_username, settings.mqtt_password)
    publisher = Publisher(client)
    publisher.publish_door_command("vehicle-example")


if __name__ == "__main__":
    main()
