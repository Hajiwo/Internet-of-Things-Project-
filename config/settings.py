"""Application settings for Smart Garage."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

@dataclass(slots=True)
class Settings:
    """Application settings for Smart Garage."""

    # MQTT broker settings
    mqtt_broker_addr: str = os.getenv("MQTT_BROKER_ADDR", "10.81.212.71")
    mqtt_broker_port: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    backend_client_id: str = os.getenv("MQTT_BACKEND_CLIENT_ID", "backend")
    raspberry_client_id: str = os.getenv("MQTT_RASPBERRY_CLIENT_ID", "raspberrypi")
    keep_alive: int = int(os.getenv("MQTT_KEEP_ALIVE", "60"))

    # Planner runtime settings
    fast_downward_executable: str = os.getenv(
        "FAST_DOWNWARD_EXECUTABLE", "fast-downward.py"
    )
    planner_domain_path: Path = Path(
        os.getenv("PLANNER_DOMAIN_PATH", "planner/domain.pddl")
    )
    planner_problem_path: Path = Path(
        os.getenv("PLANNER_PROBLEM_PATH", "problem.pddl")
    )

    # Hardware debugging dashboard
    dashboard_host: str = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    dashboard_port: int = int(os.getenv("DASHBOARD_PORT", "8080"))

    # Sensor topics
    SENSOR_TEMPERATURE: str = "garage/sensor/temperature"
    SENSOR_LIGHT: str = "garage/sensor/light"
    SENSOR_PARKING: str = "garage/sensor/parking"

    # From Software
    EVENT_VEHICLE_ENTRY: str = "garage/camera/vehicle_entry"
    EVENT_VEHICLE_LEAVE: str = "garage/camera/vehicle_exit"

    # Actuator topics
    ACTUATOR_FAN: str = "garage/actuator/fan"
    ACTUATOR_LIGHT: str = "garage/actuator/light"
    ACTUATOR_ENTRANCE_GATE: str = "garage/actuator/entrance"
    ACTUATOR_EXIT_GATE: str = "garage/actuator/exit"

    parking_size: int = 3
    temperature_high_threshold: float = 30.0
    lux_dark_threshold: float = 100.0

settings = Settings()
