from config.settings import settings
from context.manager import ContextManager
from models.event import MQTTEvent


def test_vehicle_entry_accepts_license_alias() -> None:
    manager = ContextManager()

    manager.update_vehicle_entry({"license": "BN9123", "enter_time": "2026-07-02T15:30:20"})

    assert manager.context.current_vehicles["BN9123"] == "2026-07-02T15:30:20"
    assert manager.context.vehicle_waiting_to_enter is True


def test_vehicle_leave_accepts_license_alias() -> None:
    manager = ContextManager()
    manager.context.current_vehicles["BN9123"] = "2026-07-02T15:30:20"

    manager.update_vehicle_leave({"license": "BN9123"})

    assert "BN9123" not in manager.context.current_vehicles
    assert manager.context.vehicle_waiting_to_leave is True


def test_event_handler_filters_sequence_numbers_per_topic() -> None:
    manager = ContextManager()

    assert manager.event_handler(
        MQTTEvent(settings.SENSOR_TEMPERATURE, {"sequence_number": 1, "temperature": 35})
    )
    assert not manager.event_handler(
        MQTTEvent(settings.SENSOR_TEMPERATURE, {"sequence_number": 1, "temperature": 20})
    )
    assert manager.event_handler(
        MQTTEvent(settings.SENSOR_LIGHT, {"sequence_number": 1, "lux": 50})
    )

    assert manager.context.temperature == 35.0
    assert manager.context.lux == 50.0


def test_invalid_payload_does_not_consume_sequence_number() -> None:
    manager = ContextManager()

    assert not manager.event_handler(
        MQTTEvent(settings.SENSOR_TEMPERATURE, {"sequence_number": 1, "temperature": "hot"})
    )
    assert manager.event_handler(
        MQTTEvent(settings.SENSOR_TEMPERATURE, {"sequence_number": 1, "temperature": 31})
    )
    assert manager.context.temperature == 31.0


def test_unknown_vehicle_exit_does_not_terminate_backend() -> None:
    manager = ContextManager()

    assert manager.event_handler(
        MQTTEvent(
            settings.EVENT_VEHICLE_LEAVE,
            {"sequence_number": 1, "license_plate": "UNKNOWN"},
        )
    )
    assert manager.context.vehicle_waiting_to_leave is True


def test_parking_message_requires_valid_position_and_boolean_state() -> None:
    manager = ContextManager()

    assert not manager.event_handler(
        MQTTEvent(
            settings.SENSOR_PARKING,
            {"sequence_number": 1, "position": 3, "on_occupy": True},
        )
    )
    assert not manager.event_handler(
        MQTTEvent(
            settings.SENSOR_PARKING,
            {"sequence_number": 1, "position": 0, "on_occupy": 1},
        )
    )
    assert manager.event_handler(
        MQTTEvent(
            settings.SENSOR_PARKING,
            {"sequence_number": 1, "position": 0, "on_occupy": True},
        )
    )
    assert manager.context.positions_occupied == [True, False, False]
