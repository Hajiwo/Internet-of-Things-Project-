"""Small JSON-lines publish/subscribe broker used for software-only testing."""

from __future__ import annotations

import json
import socketserver
import threading
from collections import defaultdict
from typing import Any


class BrokerState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.subscribers: dict[str, set[BrokerRequestHandler]] = defaultdict(set)

    def subscribe(self, topic: str, handler: BrokerRequestHandler) -> None:
        with self.lock:
            self.subscribers[topic].add(handler)

    def remove(self, handler: BrokerRequestHandler) -> None:
        with self.lock:
            for subscribers in self.subscribers.values():
                subscribers.discard(handler)

    def publish(self, topic: str, payload: Any) -> int:
        with self.lock:
            subscribers = list(self.subscribers.get(topic, set()))
        message = {"type": "message", "topic": topic, "payload": payload}
        for subscriber in subscribers:
            subscriber.send_json(message)
        return len(subscribers)


class BrokerRequestHandler(socketserver.StreamRequestHandler):
    server: BrokerTCPServer

    def handle(self) -> None:
        try:
            for raw_line in self.rfile:
                if not raw_line.strip():
                    continue
                try:
                    self.handle_message(json.loads(raw_line.decode("utf-8")))
                except json.JSONDecodeError as error:
                    self.send_json({"type": "error", "message": str(error)})
        finally:
            self.server.state.remove(self)

    def handle_message(self, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        topic = message.get("topic")
        if message_type == "subscribe" and isinstance(topic, str):
            self.server.state.subscribe(topic, self)
            self.send_json({"type": "subscribed", "topic": topic})
        elif message_type == "publish" and isinstance(topic, str):
            count = self.server.state.publish(topic, message.get("payload"))
            self.send_json(
                {"type": "published", "topic": topic, "subscribers": count}
            )
        else:
            self.send_json({"type": "error", "message": "invalid broker request"})

    def send_json(self, message: dict[str, Any]) -> None:
        try:
            self.wfile.write(json.dumps(message).encode("utf-8") + b"\n")
            self.wfile.flush()
        except OSError:
            self.server.state.remove(self)


class BrokerTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, BrokerRequestHandler)
        self.state = BrokerState()
