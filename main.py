"""Entry point for the Smart Garage application."""
from mqtt.client import MQTTClient
from mqtt.eventDispatcher import MQTTEventDispatcher
from mqtt.topics import SensorTopics, CommandTopics

def main() -> None:
    """Run the application."""
    print("Backend now starts running")

    mqtt_client = MQTTClient()
    event_dispatcher = MQTTEventDispatcher()
    sensor_topics = SensorTopics()
    sensor_topics_list = sensor_topics.get_topics()
    for sensor_topic in sensor_topics_list:
        mqtt_client.subscribe(sensor_topic, event_dispatcher.push_event)
    while True:
        event = event_dispatcher.get_event()
        #Process(event)



if __name__ == "__main__":
    main()
