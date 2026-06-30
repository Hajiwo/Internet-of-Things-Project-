"""Event models."""

from dataclasses import dataclass


@dataclass(slots=True)
class Event:
    """Represent a garage event."""

    name: str
    details: dict[str, str] | None = None
