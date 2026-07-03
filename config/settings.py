"""Application settings for Smart Garage."""

from dataclasses import dataclass

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

settings = Settings()
