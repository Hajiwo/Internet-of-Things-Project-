"""Standalone broker simulator for Smart Garage sensor messages.

Run this file first, then start one or more subscriber and publisher
simulators in separate terminals.
"""

from __future__ import annotations

import json
import socketserver
import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Any


HOST = "127.0.0.1"
PORT = 18830
MQTTCallback = Callable[[str, dict[str, Any]], None]


class BrokerSimulator:
    """In-memory broker for direct unit-style simulations."""

    def __init__(self) -> None:
        self.subscribers: dict[str, list[MQTTCallback]] = defaultdict(list)

    def subscribe(self, topic: str, callback: MQTTCallback) -> None:
        """Register a callback for a topic."""

        self.subscribers[topic].append(callback)
        print(f"[broker] subscriber registered for {topic}")

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Deliver a payload to all subscribers of the topic."""

        callbacks = list(self.subscribers.get(topic, []))
        print(f"[broker] publisher sent {topic}: {payload}")
        print(f"[broker] notifying {len(callbacks)} subscriber(s)")
        for callback in callbacks:
            callback(topic, payload)


class BrokerState:
    """Shared subscriber registry for the TCP broker."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.subscribers: dict[str, set[BrokerRequestHandler]] = defaultdict(set)

    def subscribe(self, topic: str, handler: BrokerRequestHandler) -> None:
        with self.lock:
            self.subscribers[topic].add(handler)
            count = len(self.subscribers[topic])
        print(f"[broker] subscriber connected to {topic} ({count} total)")

    def remove(self, handler: BrokerRequestHandler) -> None:
        with self.lock:
            for subscribers in self.subscribers.values():
                subscribers.discard(handler)

    def publish(self, topic: str, payload: dict[str, Any]) -> int:
        with self.lock:
            subscribers = list(self.subscribers.get(topic, set()))

        print(f"\n[broker] publisher sent {topic}: {payload}")
        print(f"[broker] notifying {len(subscribers)} subscriber(s)")
        message = {"type": "message", "topic": topic, "payload": payload}
        for subscriber in subscribers:
            subscriber.send_json(message)
        return len(subscribers)


class BrokerRequestHandler(socketserver.StreamRequestHandler):
    """Handle one simulator client connection."""

    server: BrokerTCPServer

    def handle(self) -> None:
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        print(f"[broker] client connected: {peer}")
        try:
            for raw_line in self.rfile:
                if not raw_line.strip():
                    continue
                try:
                    message = json.loads(raw_line.decode("utf-8"))
                    self.handle_message(message)
                except json.JSONDecodeError as exc:
                    self.send_json({"type": "error", "message": f"invalid JSON: {exc}"})
        finally:
            self.server.state.remove(self)
            print(f"[broker] client disconnected: {peer}")

    def handle_message(self, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        topic = message.get("topic")

        if message_type == "subscribe" and isinstance(topic, str):
            self.server.state.subscribe(topic, self)
            self.send_json({"type": "subscribed", "topic": topic})
            return

        if message_type == "publish" and isinstance(topic, str):
            payload = message.get("payload", {})
            if not isinstance(payload, dict):
                self.send_json({"type": "error", "message": "payload must be an object"})
                return
            subscriber_count = self.server.state.publish(topic, payload)
            self.send_json({"type": "published", "topic": topic, "subscribers": subscriber_count})
            return

        self.send_json({"type": "error", "message": f"unknown message: {message}"})

    def send_json(self, message: dict[str, Any]) -> None:
        data = json.dumps(message).encode("utf-8") + b"\n"
        try:
            self.wfile.write(data)
            self.wfile.flush()
        except OSError:
            self.server.state.remove(self)


class BrokerTCPServer(socketserver.ThreadingTCPServer):
    """TCP server with shared broker state."""

    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, BrokerRequestHandler)
        self.state = BrokerState()


def main() -> None:
    """Start the standalone broker simulator."""

    with BrokerTCPServer((HOST, PORT)) as server:
        print(f"[broker] simulator running on {HOST}:{PORT}")
        print("[broker] start subscriber and publisher simulators in separate terminals")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[broker] stopped")


if __name__ == "__main__":
    main()
