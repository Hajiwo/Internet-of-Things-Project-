"""
MQTT topics used by the backend
"""

from dataclasses import dataclass

class SensorTopics:
    """MQTT topics for garage sensors."""
    SENSOR_TEMPERATURE = "garage/sensor/temperature"
    SENSOR_LIGHT = "garage/sensor/light"
    PARKING = "garage/sensor/parking"
    LICENSE = "garage/sensor/license"

    def get_topics(self) -> list[str]:
        """Return a list of all sensor topics."""
        return [
            self.SENSOR_TEMPERATURE,
            self.SENSOR_LIGHT,
            self.PARKING,
            self.LICENSE,
        ]

class ActuatorTopics:
    """MQTT topics for actuators"""