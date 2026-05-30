from __future__ import annotations

from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.event_emitter import EventEmitter


class ValueObject(BaseSealed):
    """Domain Value Object base (immutable) with domain events."""

    def __init__(self, **kwargs) -> None:
        object.__setattr__(self, "_event_emitter", EventEmitter())
        super().__init__(**kwargs)
