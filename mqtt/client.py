import paho.mqtt.client as mqtt
import json
from config.settings import settings
from typing import Any, Callable

MQTTCallback = Callable[[str, dict[str, Any]], None]
"""
A callback function for handling incoming MQTT messages.
para: topic, payload
"""

class MQTTClient:
    """MQTT client for communication"""

    def __init__(self):
        self.client = mqtt.Client(settings.backend_client_id)

        self.host = settings.mqtt_broker_addr
        self.port = settings.mqtt_broker_port
        self.keep_alive = settings.keep_alive

    def connect(self):
        self.client.connect(self.host, self.port, self.keep_alive)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, topic: str, payload: dict[str, Any]):
        self.client.publish(topic, json.dumps(payload), qos=1)
    
    def subscribe(self, topic: str, callback: MQTTCallback):
        
        def on_message(client, userdata, msg):
            payload = json.loads(msg.payload.decode("utf-8"))
            callback(msg.topic, payload)

        self.client.subscribe(topic, qos=1)
        self.client.message_callback_add(topic, on_message)
    
    def run(self):
        self.connect()
        try:
            while True:
                pass  
        except KeyboardInterrupt:
            self.disconnect()