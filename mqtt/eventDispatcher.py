"""Receive sensor messages from MQTT topics."""

import queue
from typing import Any

from models.event import MQTTEvent

class MQTTEventDispatcher:
    """Handler for processing events from MQTT topics"""
    def __init__(self):
        self.__queue:  queue.Queue[MQTTEvent] = queue.Queue()
    
    def push_event(self, topic: str, payload: dict[str, Any]):
        """
        Dispatch an event to the callback function.
        It's the callback function of the MQTT client that will call this method when a message is received.
        """
        event = MQTTEvent(topic, payload)
        self.__queue.put(event)

    def get_event(self) -> MQTTEvent: 
        """Get the next event from the queue."""
        return self.__queue.get()
