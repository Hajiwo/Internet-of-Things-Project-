"""Smart Garage production runtime and MQTT hardware smoke test."""

import argparse
import logging
import subprocess
import time
from pathlib import Path
from typing import Any

from config.settings import settings
from context.manager import ContextManager
from executor.executor import Executor
from models.event import MQTTEvent
from mqtt.client import MQTTClient
from mqtt.eventDispatcher import MQTTEventDispatcher
from mqtt.publisher import Publisher
from mqtt.topics import ActuatorTopics, SensorTopics
from planner.fast_downward import FastDownward
from planner.planner import AIPlanner

PROJECT_ROOT = Path(__file__).resolve().parent
logger = logging.getLogger("smart-garage")


def _project_path(path: Path) -> Path:
    """Resolve a configured project-relative path."""

    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> None:
    """Run the sensor-to-planner-to-actuator production pipeline."""

    mqtt_client = MQTTClient()
    event_dispatcher = MQTTEventDispatcher()
    context_manager = ContextManager()
    publisher = Publisher(mqtt_client)
    executor = Executor(publisher, context_manager.context)
    planner = AIPlanner(
        backend=FastDownward(settings.fast_downward_executable),
        domain_path=_project_path(settings.planner_domain_path),
        problem_path=_project_path(settings.planner_problem_path),
    )

    logger.info("Starting Smart Garage backend")
    try:
        mqtt_client.connect()
        for topic in SensorTopics().get_topics():
            mqtt_client.subscribe(topic, event_dispatcher.push_event)

        logger.info("Backend is ready and waiting for Raspberry Pi messages")
        while True:
            event = event_dispatcher.get_event()
            if not context_manager.event_handler(event):
                continue

            _log_event(event, context_manager)
            try:
                plan = planner.plan(context_manager.context)
                commands = executor.execute(plan.actions)
            except (FileNotFoundError, subprocess.CalledProcessError, RuntimeError) as error:
                logger.error("Planning or command publishing failed: %s", error)
                continue

            if commands:
                logger.info(
                    "Published actuator commands: %s",
                    ", ".join(
                        f"{command.topic} -> {command.payload!r}" for command in commands
                    ),
                )
            else:
                logger.info("Planner returned no actuator changes")
    except KeyboardInterrupt:
        logger.info("Backend stopped by user")
    except (ConnectionError, OSError, RuntimeError) as error:
        logger.error("Backend startup failed: %s", error)
    finally:
        mqtt_client.disconnect()


def _log_event(event: MQTTEvent, context_manager: ContextManager) -> None:
    context = context_manager.context
    logger.info("Accepted MQTT event on %s: %s", event.topic, event.payload)
    logger.info(
        "Context: temperature=%s, light=%s, parking=%s, fan=%s, light_on=%s, "
        "entrance_gate=%s, exit_gate=%s",
        context.temperature,
        context.lux,
        context.positions_occupied,
        context.fan,
        context.light,
        context.entrance_gate,
        context.exit_gate,
    )


def test_connecting() -> None:
    """Print sensor data and publish a hardware-compatible fan command."""

    mqtt_client = MQTTClient()

    def show_received_message(topic: str, payload: dict[str, Any]) -> None:
        print(f"[RECEIVED] topic={topic}, payload={payload}", flush=True)

    print(
        f"Detecting MQTT broker at {settings.mqtt_broker_addr}:"
        f"{settings.mqtt_broker_port} ...",
        flush=True,
    )

    try:
        mqtt_client.connect()
        print("[CONNECTED] MQTT broker detected.", flush=True)
        for topic in SensorTopics().get_topics():
            mqtt_client.subscribe(topic, show_received_message)
            print(f"[SUBSCRIBED] {topic}", flush=True)

        test_topic = ActuatorTopics().ACTUATOR_FAN
        print("Press Ctrl+C to stop the test.", flush=True)
        while True:
            payload = "on"
            mqtt_client.publish(test_topic, payload)
            print(f"[PUBLISHED] topic={test_topic}, payload={payload!r}", flush=True)
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nMQTT hardware test stopped.", flush=True)
    except (ConnectionError, OSError, RuntimeError) as error:
        print(f"[CONNECTION FAILED] {error}", flush=True)
    finally:
        mqtt_client.disconnect()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="receive sensor messages and publish a fan test command every 3 seconds",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    arguments = parse_args()
    if arguments.test_connection:
        test_connecting()
    else:
        main()
