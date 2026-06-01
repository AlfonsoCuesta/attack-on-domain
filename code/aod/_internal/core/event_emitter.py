import contextvars
from datetime import datetime, timezone

from .base_sealed import BaseSealed
from .fields.fields import Field


class Event(BaseSealed):
    emitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), init=False)


class EventEmitter:
    def __init__(self) -> None:
        self._events: list[Event] = []

    def emit(self, event: Event) -> None:
        self._events.append(event)
        collector = _event_collector.get(None)
        if collector is not None:
            collector.append(event)

    def poll_events(self) -> list[Event]:
        return list(self._events)

    def clear_events(self) -> None:
        self._events.clear()


_event_collector: contextvars.ContextVar[list[Event]] = contextvars.ContextVar("_event_collector")


class EventCollector:
    def __init__(self) -> None:
        self._events: list[Event] = []

    def __enter__(self) -> list[Event]:
        self._token = _event_collector.set(self._events)
        return self._events

    def __exit__(self, *args: object) -> None:
        _event_collector.reset(self._token)
