"""Application settings for Smart Garage."""

from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    mqtt_host: str = os.getenv("MQTT_HOST", "localhost")
    mqtt_port: int = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_username: str = os.getenv("MQTT_USERNAME", "")
    mqtt_password: str = os.getenv("MQTT_PASSWORD", "")
    fast_downward_path: str = os.getenv("FAST_DOWNWARD_PATH", "")


settings = Settings()
