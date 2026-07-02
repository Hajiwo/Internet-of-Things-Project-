"""In-memory broker used to simulate MQTT publish/subscribe behavior in tests."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any


MQTTCallback = Callable[[str, dict[str, Any]], None]


class BrokerSimulator:
	"""Route published messages to subscribed callbacks without a real broker."""

	def __init__(self) -> None:
		self.subscribers: dict[str, list[MQTTCallback]] = defaultdict(list)

	def subscribe(self, topic: str, callback: MQTTCallback) -> None:
		"""Register a callback for a topic."""

		self.subscribers[topic].append(callback)

	def publish(self, topic: str, payload: dict[str, Any]) -> None:
		"""Deliver a payload to all subscribers of the topic."""

		for callback in list(self.subscribers.get(topic, [])):
			callback(topic, payload)
