"""MQTTClient-compatible client for the local Raspberry Pi simulator."""

from __future__ import annotations

import json
import logging
import queue
import socket
import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)
SimulationCallback = Callable[[str, Any], None]


class SimulationMQTTClient:
    """Exchange JSON-lines messages with the simulator broker."""

    def __init__(self, host: str = "127.0.0.1", port: int = 18830) -> None:
        self.host = host
        self.port = port
        self.keep_alive = 60
        self._socket: socket.socket | None = None
        self._file: Any | None = None
        self._connected = False
        self._reader: threading.Thread | None = None
        self._callbacks: dict[str, list[SimulationCallback]] = defaultdict(list)
        self._responses: queue.Queue[dict[str, Any]] = queue.Queue()
        self._request_lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self._socket = socket.create_connection((self.host, self.port), timeout=5)
        self._socket.settimeout(None)
        self._file = self._socket.makefile("r", encoding="utf-8")
        self._connected = True
        self._reader = threading.Thread(
            target=self._read_messages,
            name="simulator-client-reader",
            daemon=True,
        )
        self._reader.start()
        logger.info("Connected to Raspberry Pi simulator at %s:%s", self.host, self.port)

    def disconnect(self) -> None:
        self._connected = False
        if self._socket is not None:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        if self._file is not None:
            try:
                self._file.close()
            except OSError:
                pass
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
        self._file = None
        self._socket = None
        if self._reader is not None and self._reader is not threading.current_thread():
            self._reader.join(timeout=1)
        self._reader = None

    def publish(self, topic: str, payload: Any) -> dict[str, Any]:
        return self._request({"type": "publish", "topic": topic, "payload": payload})

    def subscribe(self, topic: str, callback: SimulationCallback) -> None:
        self._callbacks[topic].append(callback)
        response = self._request({"type": "subscribe", "topic": topic})
        if response.get("type") != "subscribed":
            self._callbacks[topic].remove(callback)
            raise RuntimeError(f"Simulator subscription failed: {response}")
        logger.info("Subscribed to simulator topic %s", topic)

    def _request(self, message: dict[str, Any]) -> dict[str, Any]:
        if not self._connected or self._socket is None:
            raise RuntimeError("Raspberry Pi simulator is disconnected")
        with self._request_lock:
            data = json.dumps(message).encode("utf-8") + b"\n"
            try:
                self._socket.sendall(data)
                response = self._responses.get(timeout=5)
            except (OSError, queue.Empty) as error:
                raise RuntimeError(f"Simulator request failed: {error}") from error
        if response.get("type") == "error":
            raise RuntimeError(response.get("message", "Simulator broker error"))
        return response

    def _read_messages(self) -> None:
        try:
            while self._connected and self._file is not None:
                line = self._file.readline()
                if not line:
                    break
                message = json.loads(line)
                if message.get("type") == "message":
                    self._dispatch(message)
                else:
                    self._responses.put(message)
        except (OSError, ValueError):
            if self._connected:
                logger.exception("Simulator connection reader stopped")
        finally:
            self._connected = False

    def _dispatch(self, message: dict[str, Any]) -> None:
        topic = message.get("topic")
        payload = message.get("payload")
        if not isinstance(topic, str):
            return
        for callback in list(self._callbacks.get(topic, [])):
            try:
                callback(topic, payload)
            except Exception:
                logger.exception("Simulator callback failed on %s", topic)
