"""End-to-end runner for the Smart Garage MQTT pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	 sys.path.insert(0, str(PROJECT_ROOT))

from broker_simulator import BrokerSimulator
from simulation_broker import SimulationBroker
from simulation_publisher import SimulationPublisher


def main() -> None:
	broker = BrokerSimulator()
	subscriber = SimulationBroker(broker)
	publisher = SimulationPublisher(broker)

	subscriber.start()

	try:
		publisher.publish_demo_messages()
		print("\n[runner] final context snapshot:")
		subscriber.context_manager.print_context()
	finally:
		publisher.stop()
		subscriber.stop()


if __name__ == "__main__":
	main()