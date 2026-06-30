"""Update garage context from MQTT messages."""

from .context import GarageContext


class ContextManager:
    """Apply incoming sensor data to the current garage context."""

    def __init__(self, context: GarageContext | None = None) -> None:
        self.context = context or GarageContext()

    def apply_temperature(self, temperature: float) -> None:
        self.context.temperature = temperature
        self.context.last_event = "temperature"

    def apply_vehicle_presence(self, present: bool) -> None:
        self.context.vehicle_present = present
        self.context.last_event = "vehicle"
