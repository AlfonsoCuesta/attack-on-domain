import contextvars
from datetime import datetime, timezone

from .base_sealed import BaseSealed
from .fields.fields import Field


class Event(BaseSealed):
    """Immutable domain event. ``emitted_at`` is auto-set on construction."""

    emitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), init=False)


class IntegrationEvent(Event):
    """Marker base for events that cross bounded context boundaries."""


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


class EventsListened:
    def __init__(self) -> None:
        self._events: list[Event] = []

    def __iter__(self):
        return iter(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def __getitem__(self, index: int) -> Event:
        return self._events[index]

    def append(self, event: Event) -> None:
        self._events.append(event)

    @property
    def domain_events(self) -> list[Event]:
        return [e for e in self._events if not isinstance(e, IntegrationEvent)]

    @property
    def integration_events(self) -> list[IntegrationEvent]:
        return [e for e in self._events if isinstance(e, IntegrationEvent)]


class EventCollector:
    """Context manager that captures all events emitted via
    ``EventEmitter.emit`` while active.
    """

    def __enter__(self) -> EventsListened:
        self._listened = EventsListened()
        self._token = _event_collector.set(self._listened)
        return self._listened

    def __exit__(self, *args: object) -> None:
        _event_collector.reset(self._token)


_event_collector: contextvars.ContextVar[EventsListened] = contextvars.ContextVar(
    "_event_collector"
)
