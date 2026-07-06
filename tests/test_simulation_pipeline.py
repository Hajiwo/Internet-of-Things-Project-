from datetime import datetime
from typing import Any

from config.settings import settings
from tests.broker_simulator import BrokerSimulator
from tests.simulation_publisher import SimulationPublisher
from tests.simulation_subscriber import ActuatorMonitor, SimulationBroker


def test_sensor_messages_flow_through_backend_to_actuator_commands() -> None:
    broker = BrokerSimulator()
    backend = SimulationBroker(broker)
    actuator_messages: list[tuple[str, Any]] = []

    backend.start()
    for topic in [
        settings.ACTUATOR_FAN,
        settings.ACTUATOR_LIGHT,
        settings.ACTUATOR_ENTRANCE_GATE,
        settings.ACTUATOR_EXIT_GATE,
    ]:
        broker.subscribe(topic, lambda topic, payload: actuator_messages.append((topic, payload)))

    publisher = SimulationPublisher(broker)
    publisher.publish(settings.SENSOR_TEMPERATURE, {"temperature": 35.0})
    assert actuator_messages == [(settings.ACTUATOR_FAN, "on")]

    publisher.publish(settings.SENSOR_LIGHT, {"lux": 20.0})
    assert actuator_messages == [
        (settings.ACTUATOR_FAN, "on"),
        (settings.ACTUATOR_LIGHT, "on"),
    ]

    publisher.publish(
        settings.EVENT_VEHICLE_ENTRY,
        {
            "license_plate": "BN9123",
            "enter_time": datetime.now().isoformat(timespec="seconds"),
        },
    )

    assert (settings.ACTUATOR_FAN, "on") in actuator_messages
    assert (settings.ACTUATOR_LIGHT, "on") in actuator_messages
    assert (settings.ACTUATOR_ENTRANCE_GATE, "open") in actuator_messages


def test_actuator_monitor_subscribes_to_all_actuator_topics() -> None:
    broker = BrokerSimulator()
    monitor = ActuatorMonitor(broker)

    monitor.start()

    for topic in [
        settings.ACTUATOR_FAN,
        settings.ACTUATOR_LIGHT,
        settings.ACTUATOR_ENTRANCE_GATE,
        settings.ACTUATOR_EXIT_GATE,
    ]:
        assert topic in broker.subscribers
