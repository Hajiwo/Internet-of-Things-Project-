"""Smart Garage production runtime and MQTT hardware smoke test."""

import argparse
import logging
import shutil
import threading
import time
from pathlib import Path
from typing import Any

from config.settings import settings
from dashboard.server import DashboardServer
from mqtt.client import MQTTClient
from mqtt.topics import ActuatorTopics, SensorTopics
from planner.fast_downward import FastDownward
from planner.planner import AIPlanner
from planner.rule_backend import RulePlanningBackend
from services.backend_service import SmartGarageService

PROJECT_ROOT = Path(__file__).resolve().parent
logger = logging.getLogger("smart-garage")


def _project_path(path: Path) -> Path:
    """Resolve a configured project-relative path."""

    return path if path.is_absolute() else PROJECT_ROOT / path


def main() -> None:
    """Start MQTT subscriber/publisher, planning, camera API, and dashboard."""

    planner = _build_planner()
    backend = SmartGarageService(planner)
    dashboard = DashboardServer(
        state_provider=backend.snapshot,
        camera_handler=backend.capture_vehicle,
        host=settings.dashboard_host,
        port=settings.dashboard_port,
    )

    logger.info("Starting Smart Garage hardware debugging system")
    try:
        dashboard.start()
        logger.info(
            "Dashboard: http://localhost:%s", dashboard.address[1]
        )
        try:
            backend.start()
        except (ConnectionError, OSError, RuntimeError) as error:
            backend.last_error = str(error)
            logger.error("MQTT startup failed; dashboard remains available: %s", error)

        logger.info("Press Ctrl+C to stop all services")
        threading.Event().wait()
    except KeyboardInterrupt:
        logger.info("Smart Garage stopped by user")
    finally:
        backend.stop()
        dashboard.stop()


def _build_planner() -> AIPlanner:
    """Use Fast Downward when installed, otherwise use the debug fallback."""

    executable = settings.fast_downward_executable
    executable_exists = Path(executable).is_file() or shutil.which(executable) is not None
    if executable_exists:
        planner_backend = FastDownward(executable)
        logger.info("Using Fast Downward planner: %s", executable)
    else:
        planner_backend = RulePlanningBackend()
        logger.warning(
            "Fast Downward '%s' was not found; using local hardware-debug rules",
            executable,
        )

    return AIPlanner(
        backend=planner_backend,
        domain_path=_project_path(settings.planner_domain_path),
        problem_path=_project_path(settings.planner_problem_path),
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
