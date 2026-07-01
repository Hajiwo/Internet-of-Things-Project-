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

sensorTopic = SensorTopics()

class ActuatorTopics:
    """MQTT topics for actuators"""