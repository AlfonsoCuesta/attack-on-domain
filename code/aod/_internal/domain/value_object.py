from __future__ import annotations

from typing import Any

from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.event_emitter import EventEmitter
from aod._internal.core.fields.fields import PrivateField
from aod._internal.core.reconstructable import ReconstructMixin


class ValueObject(ReconstructMixin, BaseSealed):
    """Domain Value Object base (immutable) with domain events."""

    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)

    def __eq__(self, other: Any) -> bool:
        if type(self) is not type(other):
            return False
        for field in self.__model_fields__:
            if field.startswith("_"):
                continue
            if getattr(self, field) != getattr(other, field):
                return False
        return True

    def __hash__(self) -> int:
        public = tuple(getattr(self, f) for f in self.__model_fields__ if not f.startswith("_"))
        return hash(public)
