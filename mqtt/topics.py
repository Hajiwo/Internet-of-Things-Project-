"""MQTT topics used by the backend."""

from config.settings import settings

class SensorTopics:
    """MQTT topics for garage sensors."""
    def __init__(self):
        self.SENSOR_TEMPERATURE = settings.SENSOR_TEMPERATURE
        self.SENSOR_LIGHT = settings.SENSOR_LIGHT
        self.PARKING = settings.PARKING
        self.VEHICLE_ENTRY = settings.VEHICLE_ENTRY
        self.VEHICLE_LEAVE = settings.VEHICLE_LEAVE

    def get_topics(self) -> list[str]:
        """Return a list of all sensor topics."""
        return [
            self.SENSOR_TEMPERATURE,
            self.SENSOR_LIGHT,
            self.PARKING,
            self.VEHICLE_ENTRY,
            self.VEHICLE_LEAVE,
        ]

class ActuatorTopics:
    """MQTT topics for actuators"""