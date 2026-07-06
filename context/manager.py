"""Update garage context from MQTT messages."""

from context.context import Context
from config.settings import settings
from models.event import MQTTEvent

class ContextManager:
    """Apply incoming sensor data to the current garage context."""
    def __init__(self, context: Context | None = None) -> None:
        self.context = context if context is not None else Context()
        self.msg_sequences: dict[str, int] = {
            settings.SENSOR_TEMPERATURE: 0,
            settings.SENSOR_LIGHT: 0,
            settings.SENSOR_PARKING: 0,
            settings.EVENT_VEHICLE_ENTRY: 0,
            settings.EVENT_VEHICLE_LEAVE: 0,
        }

    def event_handler(self, event: MQTTEvent) -> None:
        """Handle event and filter out duplicates based on sequence number."""
        topic = event.topic
        payload = event.payload
        sequence_number = payload.get("sequence_number", payload.get("sequence", 0))

        if sequence_number > self.msg_sequences.get(topic, 0):
            self.msg_sequences[topic] = sequence_number
            if topic == settings.SENSOR_TEMPERATURE:
                self.update_temperature(payload)
            elif topic == settings.SENSOR_LIGHT:
                self.update_light(payload)
            elif topic == settings.SENSOR_PARKING:
                self.update_parking(payload)    
            elif topic == settings.EVENT_VEHICLE_ENTRY:
                self.update_vehicle_entry(payload)
            elif topic == settings.EVENT_VEHICLE_LEAVE:
                self.update_vehicle_leave(payload)

    def update_temperature(self, payload: dict) -> None:
        """Update temperature in context. """
        self.context.temperature = payload.get("temperature")

    def update_light(self, payload: dict) -> None:
        """Update light in context. """
        self.context.lux = payload.get("lux")

    def update_parking(self, payload: dict) -> None:
        """Update parking occupancy in context. """
        position = payload.get("position")
        on_occupy = payload.get("on_occupy")
        if position is not None and 0 <= position < settings.parking_size:
            self.context.positions_occupied[position] = on_occupy

    def update_vehicle_entry(self, payload: dict) -> None:
        """Update vehicle entry in context. """
        license_plate = payload.get("license_plate") or payload.get("license")
        enter_time = payload.get("enter_time")
        if license_plate and enter_time:
            self.context.current_vehicles[license_plate] = enter_time

    def update_vehicle_leave(self, payload: dict) -> None:
        """update vehicle leave in context"""
        license_plate = payload.get("license_plate") or payload.get("license")
        if license_plate in self.context.current_vehicles:
            del self.context.current_vehicles[license_plate]
        else:
            print(f"Warning: Vehicle with license plate {license_plate} not found in current vehicles.")
            exit(1)  # Exit the program with an error code

    def print_context(self) -> None:
        """Print the current context for debugging."""
        print("Current Garage Context:")
        print(f"Temperature: {self.context.temperature}")
        print(f"Lux: {self.context.lux}")
        print(f"Positions Occupied: {self.context.positions_occupied}")
        print(f"Current Vehicles: {list(self.context.current_vehicles.keys())}")
        print(f"Fan On: {self.context.fan}")
        print(f"Light On: {self.context.light}")
        print(f"Entrance Gate Open: {self.context.entrance_gate}")
        print(f"Exit Gate Open: {self.context.exit_gate}")
