"""Generic helper functions."""


def normalize_topic(topic: str) -> str:
    """Normalize MQTT topic text."""

    return topic.strip().lower()
