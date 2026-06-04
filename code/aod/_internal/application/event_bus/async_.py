from __future__ import annotations

from abc import abstractmethod

from aod._internal.application.port import Port
from aod._internal.core.event_emitter import Event


class EventBus(Port):
    @abstractmethod
    async def publish(self, *events: Event) -> None: ...
