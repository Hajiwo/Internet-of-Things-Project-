"""MQTT topics used by the backend."""

from config.settings import settings

class SensorTopics:
    """MQTT topics for garage sensors."""
    def __init__(self):
        self.SENSOR_TEMPERATURE = settings.SENSOR_TEMPERATURE
        self.SENSOR_LIGHT = settings.SENSOR_LIGHT
        self.SENSOR_PARKING = settings.SENSOR_PARKING
        self.EVENT_VEHICLE_ENTRY = settings.EVENT_VEHICLE_ENTRY
        self.EVENT_VEHICLE_LEAVE = settings.EVENT_VEHICLE_LEAVE

        self.PARKING = self.SENSOR_PARKING
        self.VEHICLE_ENTRY = self.EVENT_VEHICLE_ENTRY
        self.VEHICLE_LEAVE = self.EVENT_VEHICLE_LEAVE

    def get_topics(self) -> list[str]:
        """Return a list of all sensor topics."""
        return [
            self.SENSOR_TEMPERATURE,
            self.SENSOR_LIGHT,
            self.SENSOR_PARKING,
            self.EVENT_VEHICLE_ENTRY,
            self.EVENT_VEHICLE_LEAVE,
        ]

class ActuatorTopics:
    """MQTT topics for garage actuators."""

    def __init__(self):
        self.ACTUATOR_FAN = settings.ACTUATOR_FAN
        self.ACTUATOR_LIGHT = settings.ACTUATOR_LIGHT
        self.ACTUATOR_ENTRANCE_GATE = settings.ACTUATOR_ENTRANCE_GATE
        self.ACTUATOR_EXIT_GATE = settings.ACTUATOR_EXIT_GATE

    def get_topics(self) -> list[str]:
        """Return a list of all actuator topics."""

        return [
            self.ACTUATOR_FAN,
            self.ACTUATOR_LIGHT,
            self.ACTUATOR_ENTRANCE_GATE,
            self.ACTUATOR_EXIT_GATE,
        ]
