import threading

from mqtt.simulation_client import SimulationMQTTClient
from simulator.broker import BrokerTCPServer


def test_simulation_clients_publish_and_subscribe() -> None:
    server = BrokerTCPServer(("127.0.0.1", 0))
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    port = server.server_address[1]
    subscriber = SimulationMQTTClient("127.0.0.1", port)
    publisher = SimulationMQTTClient("127.0.0.1", port)
    received: list[tuple[str, object]] = []
    delivered = threading.Event()

    try:
        subscriber.connect()
        publisher.connect()
        subscriber.subscribe(
            "garage/actuator/entrance",
            lambda topic, payload: (received.append((topic, payload)), delivered.set()),
        )

        receipt = publisher.publish("garage/actuator/entrance", "open")

        assert receipt["type"] == "published"
        assert delivered.wait(timeout=2)
        assert received == [("garage/actuator/entrance", "open")]
    finally:
        publisher.disconnect()
        subscriber.disconnect()
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)
