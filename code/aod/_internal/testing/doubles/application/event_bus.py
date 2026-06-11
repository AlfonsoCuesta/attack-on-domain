from __future__ import annotations

from aod._internal.core.event_emitter import Event
from aod._internal.core.fields.fields import PrivateField
from aod._internal.application.event_bus.event_bus import EventBus
from aod._internal.application.event_bus.event_bus import AsyncEventBus


class SpyEventBus(EventBus):
    _published: list[Event] = PrivateField(default_factory=list)

    @property
    def published(self) -> list[Event]:
        return list(self._published)

    def publish(self, *events: Event) -> None:
        self._published.extend(events)


class AsyncSpyEventBus(AsyncEventBus):
    _published: list[Event] = PrivateField(default_factory=list)

    @property
    def published(self) -> list[Event]:
        return list(self._published)

    async def publish(self, *events: Event) -> None:
        self._published.extend(events)
