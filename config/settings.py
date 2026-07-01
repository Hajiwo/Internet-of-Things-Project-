"""Application settings for Smart Garage."""

from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
    """Application settings for Smart Garage."""

    # MQTT broker settings
    mqtt_broker_addr: str = "localhost"
    mqtt_broker_port: int = 1883
    backend_client_id: str = "backend"
    raspberry_client_id: str = "raspberrypi"
    keep_alive: int = 60

    # Sensor topics
    SENSOR_TEMPERATURE: str = "garage/sensor/temperature"
    SENSOR_LIGHT: str = "garage/sensor/light"
    PARKING: str = "garage/sensor/parking"
    LICENSE: str = "garage/sensor/license"
    BILLING: str = "garage/sensor/billing"

    parking_positions: int = 4

settings = Settings()
