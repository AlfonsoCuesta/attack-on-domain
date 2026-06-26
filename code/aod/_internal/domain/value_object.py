from __future__ import annotations

from typing import Any

from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import InvalidValueObjectFieldError
from aod._internal.core.event_emitter import EventEmitter
from aod._internal.core.fields.fields import _IDENTITY_MARKER, PrivateField
from aod._internal.core.reconstructable import ReconstructMixin
from pydantic.fields import FieldInfo


class ValueObject(ReconstructMixin, BaseSealed):
    """Domain Value Object base (immutable) with domain events."""

    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for name, value in cls.__dict__.items():
            if isinstance(value, FieldInfo) and _IDENTITY_MARKER in value.metadata:
                raise InvalidValueObjectFieldError(cls.__name__, name)

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
