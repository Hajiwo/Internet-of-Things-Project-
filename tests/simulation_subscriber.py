"""Full-pipeline simulator for Smart Garage backend planning."""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from context.manager import ContextManager
from executor.executor import Executor
from models.event import MQTTEvent
from models.plan import Plan
from mqtt.publisher import Publisher
from mqtt.topics import ActuatorTopics, SensorTopics
from planner.actions import PlannerAction
from planner.planner import AIPlanner
from tests.broker_simulator import HOST, PORT, BrokerSimulator


class BrokerSimulatorClient:
    """JSON-lines subscriber client for the standalone broker simulator."""

    def __init__(self, host: str = HOST, port: int = PORT) -> None:
        self.host = host
        self.port = port
        self.socket: socket.socket | None = None
        self.file = None

    def connect(self) -> None:
        self.socket = socket.create_connection((self.host, self.port))
        self.file = self.socket.makefile("r", encoding="utf-8")

    def disconnect(self) -> None:
        if self.file is not None:
            self.file.close()
        if self.socket is not None:
            self.socket.close()

    def subscribe(self, topic: str, callback: Any | None = None) -> None:
        self._send({"type": "subscribe", "topic": topic})
        if self.file is None:
            raise RuntimeError("subscriber is not connected")
        receipt = json.loads(self.file.readline())
        if receipt.get("type") == "subscribed":
            print(f"[subscriber] subscribed to {topic}")

    def publish(self, topic: str, payload: Any) -> dict[str, Any]:
        """Publish actuator commands back to the simulator broker."""

        if self.socket is None or self.file is None:
            raise RuntimeError("subscriber is not connected")
        self._send({"type": "publish", "topic": topic, "payload": payload})
        return json.loads(self.file.readline())

    def listen(self, callback: Any) -> None:
        if self.file is None:
            raise RuntimeError("subscriber is not connected")
        for line in self.file:
            message = json.loads(line)
            if message.get("type") == "message":
                callback(message["topic"], message["payload"])
            elif message.get("type") == "error":
                print(f"[subscriber] broker error: {message.get('message')}")

    def _send(self, message: dict[str, Any]) -> None:
        if self.socket is None:
            raise RuntimeError("subscriber is not connected")
        self.socket.sendall(json.dumps(message).encode("utf-8") + b"\n")


class SimulationBroker:
    """Subscribe to sensor topics and run backend planning."""

    def __init__(self, broker: BrokerSimulator | BrokerSimulatorClient | None = None) -> None:
        self.broker = broker if broker is not None else BrokerSimulatorClient()
        self.topics = SensorTopics().get_topics()
        self.context_manager = ContextManager()
        self.publisher = Publisher(self.broker)  # type: ignore[arg-type]
        self.executor = Executor(self.publisher)
        self.planner = AIPlanner(
            backend=SimulationPlanningBackend(),
            domain_path=PROJECT_ROOT / "planner" / "domain.pddl",
            problem_path=PROJECT_ROOT / "tests" / "simulation_problem.pddl",
        )

        self.connect = self.broker.connect if hasattr(self.broker, "connect") else lambda: None
        self.disconnect = self.broker.disconnect if hasattr(self.broker, "disconnect") else lambda: None

    def start(self) -> None:
        """Connect and subscribe to all sensor topics."""

        self.connect()
        print(f"[subscriber] connected to broker simulator at {HOST}:{PORT}")
        print("[subscriber] subscribing topics:")
        for topic in self.topics:
            self.broker.subscribe(topic, self._on_message)

    def listen_forever(self) -> None:
        """Listen to broker messages until the user stops the process."""

        if hasattr(self.broker, "listen"):
            self.broker.listen(self._on_message)
            return

        print("[subscriber] direct in-memory mode is ready")
        while True:
            pass

    def _on_message(self, topic: str, payload: dict[str, Any]) -> None:
        """Update context, plan desired actions, and publish actuator commands."""

        print(f"\n[subscriber] received on {topic}: {payload}")
        if not isinstance(payload, dict):
            print("[backend] ignored non-object sensor payload")
            return

        event = MQTTEvent(topic=topic, payload=payload)
        try:
            self.context_manager.event_handler(event)
        except SystemExit:
            print("[subscriber] context manager rejected the message")
            return

        self.context_manager.print_context()
        plan = self.planner.plan(self.context_manager.context)
        self._print_plan(plan)
        self.executor.execute(plan.actions)
        self._apply_plan_to_context(plan)

    def stop(self) -> None:
        """Disconnect the MQTT client."""

        self.disconnect()

    def _print_plan(self, plan: Plan) -> None:
        if not plan.actions:
            print("[backend] planner returned no actuator actions")
            return

        actions = ", ".join(action.name for action in plan.actions)
        print(f"[backend] planner actions: {actions}")

    def _apply_plan_to_context(self, plan: Plan) -> None:
        """Apply simulated actuator effects so later plans use fresh state."""

        context = self.context_manager.context
        for action in plan.actions:
            if action.name == "turn-on-fan":
                context.fan = True
            elif action.name == "turn-off-fan":
                context.fan = False
            elif action.name == "turn-on-light":
                context.light = True
            elif action.name == "turn-off-light":
                context.light = False
            elif action.name == "open-entrance-gate":
                context.entrance_gate = True
                context.vehicle_waiting_to_enter = False
            elif action.name == "close-entrance-gate":
                context.entrance_gate = False
            elif action.name == "open-exit-gate":
                context.exit_gate = True
                context.vehicle_waiting_to_leave = False
            elif action.name == "close-exit-gate":
                context.exit_gate = False


class SimulationPlanningBackend:
    """Small deterministic planner backend for local simulator runs.

    It reads the generated PDDL problem and returns Fast-Downward-style
    action lines. This keeps the simulator self-contained when the external
    Fast Downward executable is not installed.
    """

    def run(self, domain_path: str, problem_path: str) -> str:
        problem_text = Path(problem_path).read_text(encoding="utf-8")
        init_text = _section(problem_text, ":init")
        goal_text = _section(problem_text, ":goal")
        actions: list[PlannerAction] = []

        self._append_state_action(
            actions,
            init_text,
            goal_text,
            predicate="fan-on",
            turn_on="turn-on-fan",
            turn_off="turn-off-fan",
        )
        self._append_state_action(
            actions,
            init_text,
            goal_text,
            predicate="light-on",
            turn_on="turn-on-light",
            turn_off="turn-off-light",
        )
        self._append_state_action(
            actions,
            init_text,
            goal_text,
            predicate="entrance-gate-open",
            turn_on="open-entrance-gate",
            turn_off="close-entrance-gate",
        )
        self._append_state_action(
            actions,
            init_text,
            goal_text,
            predicate="exit-gate-open",
            turn_on="open-exit-gate",
            turn_off="close-exit-gate",
        )

        return "\n".join(
            f"{index}: ({action.name})" for index, action in enumerate(actions)
        )

    def _append_state_action(
        self,
        actions: list[PlannerAction],
        init_text: str,
        goal_text: str,
        predicate: str,
        turn_on: str,
        turn_off: str,
    ) -> None:
        currently_on = _has_positive_predicate(init_text, predicate)
        should_be_on = _has_positive_predicate(goal_text, predicate)
        should_be_off = _has_negative_predicate(goal_text, predicate)

        if should_be_on and not currently_on:
            actions.append(PlannerAction(turn_on))
        elif should_be_off and currently_on:
            actions.append(PlannerAction(turn_off))


class ActuatorMonitor:
    """Subscribe to actuator topics and print backend commands."""

    def __init__(self, broker: BrokerSimulator | BrokerSimulatorClient | None = None) -> None:
        self.broker = broker if broker is not None else BrokerSimulatorClient()
        self.topics = ActuatorTopics().get_topics()

        self.connect = self.broker.connect if hasattr(self.broker, "connect") else lambda: None
        self.disconnect = self.broker.disconnect if hasattr(self.broker, "disconnect") else lambda: None

    def start(self) -> None:
        self.connect()
        print(f"[actuator] connected to broker simulator at {HOST}:{PORT}")
        print("[actuator] subscribing topics:")
        for topic in self.topics:
            self.broker.subscribe(topic, self._on_message)

    def listen_forever(self) -> None:
        if hasattr(self.broker, "listen"):
            self.broker.listen(self._on_message)
            return

        print("[actuator] direct in-memory mode is ready")
        while True:
            pass

    def stop(self) -> None:
        self.disconnect()

    def _on_message(self, topic: str, payload: Any) -> None:
        print(f"\n[actuator] command on {topic}: {payload}")


def _section(text: str, marker: str) -> str:
    start = text.find(f"({marker}")
    if start == -1:
        return ""

    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return text[start:]


def _has_positive_predicate(section_text: str, predicate: str) -> bool:
    return any(line.strip() == f"({predicate})" for line in section_text.splitlines())


def _has_negative_predicate(section_text: str, predicate: str) -> bool:
    return any(
        line.strip() == f"(not ({predicate}))" for line in section_text.splitlines()
    )


def main() -> None:
    mode = sys.argv[1].strip().lower() if len(sys.argv) > 1 else "backend"
    if mode in {"actuator", "actuators", "monitor"}:
        subscriber = ActuatorMonitor()
    else:
        subscriber = SimulationBroker()

    try:
        subscriber.start()
    except OSError as exc:
        print(f"[subscriber] cannot connect to broker at {HOST}:{PORT}: {exc}")
        print("[subscriber] start tests/broker_simulator.py first")
        return

    try:
        subscriber.listen_forever()
    except KeyboardInterrupt:
        print("\n[subscriber] stopped")
    finally:
        subscriber.stop()


if __name__ == "__main__":
    main()
