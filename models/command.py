"""Command models."""

from dataclasses import dataclass


@dataclass(slots=True)
class Command:
    """Represent a command to be sent to the garage system."""

    topic: str
    payload: str
