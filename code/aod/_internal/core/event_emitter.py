from datetime import datetime, timezone
from typing import List, Protocol, runtime_checkable

from .base_immutable import BaseImmutable
from .fields.fields import Field


class Event(BaseImmutable):
    emmited_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), init=False
    )


@runtime_checkable
class EventEmitter(Protocol):
    def _emit(self, event: Event) -> None:
        pass

    def _clear_events(self) -> None:
        pass

    def poll_events(self) -> List[Event]:
        pass
