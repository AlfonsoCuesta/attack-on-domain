from __future__ import annotations

from typing import List

from aod._internal.core.base_immutable import BaseImmutable
from aod._internal.core.event_emitter import Event
from aod._internal.core.fields import PrivateField


class ValueObject(BaseImmutable):
    """Domain Value Object base (immutable) with domain events."""

    _events: List[Event] = PrivateField(default_factory=list)

    def _emit(self, event: Event) -> None:
        self._events.append(event)

    def _clear_events(self) -> None:
        self._events.clear()

    def poll_events(self) -> List[Event]:
        return list(self._events)
