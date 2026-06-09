from __future__ import annotations

from aod._internal.application.event_bus.event_bus import EventBus
from aod._internal.core.event_emitter import Event


class NullEventBus(EventBus):
    def publish(self, *events: Event) -> None: ...
