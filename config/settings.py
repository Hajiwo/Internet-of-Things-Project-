"""Application settings for Smart Garage."""

from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
    mqtt_broker_addr: str = "localhost"
    mqtt_broker_port: int = 1883
    backend_client_id: str = "backend"
    raspberry_client_id: str = "raspberrypi"
    keep_alive: int = 60


settings = Settings()
