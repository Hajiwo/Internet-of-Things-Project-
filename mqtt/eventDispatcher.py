"""Receive sensor messages from MQTT topics."""

from typing import Callable
from .client import *
from .topics import SensorTopics
from dataclasses import dataclass
import queue

@dataclass(slots=True)
class MQTTEvent:
    """Represent an event received from an MQTT topic."""
    topic: str
    payload: dict[str, Any]


class MQTTEventDispatcher:
    """Handler for processing events from MQTT topics"""
    def __init__(self):
        self.queue = queue.Queue()
    
    def dispatch(self, topic: str, payload: dict[str, Any]):
        """
        Dispatch an event to the callback function.
        It's the callback function of the MQTT client that will call this method when a message is received.
        """
        event = MQTTEvent(topic, payload)
        self.queue.put(event)

    def run(self):
        """Start the event handler loop."""
        while True:
            if not self.queue.empty():
                event = self.queue.get()
                self.callback(event)
