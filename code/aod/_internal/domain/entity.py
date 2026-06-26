from __future__ import annotations

from typing import Any, get_type_hints

from aod._internal.core.base_guarded import BaseGuarded, inherit_context
from aod._internal.core.domain_exception import (
    InvalidIdentityFieldTypeError,
    NoEntityIdException,
    TooManyEntityIdsException,
)
from aod._internal.core.event_emitter import EventEmitter
from aod._internal.core.fields.fields import _IDENTITY_MARKER, PrivateField
from aod._internal.core.reconstructable import ReconstructMixin
from aod._internal.domain.entity_id import EntityId
from pydantic.fields import FieldInfo


class Entity(ReconstructMixin, BaseGuarded):
    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__name__ in ("RootEntity"):
            return

        identity_fields = []
        for name, value in cls.__dict__.items():
            if isinstance(value, FieldInfo) and _IDENTITY_MARKER in value.metadata:
                identity_fields.append(name)

        if identity_fields:
            if len(identity_fields) > 1:
                raise TooManyEntityIdsException(cls.__name__)
            field_name = identity_fields[0]
            try:
                hints = get_type_hints(cls)
                field_type = hints.get(field_name)
            except Exception:
                field_type = cls.__annotations__.get(field_name)
            if (
                field_type is None
                or not isinstance(field_type, type)
                or not issubclass(field_type, EntityId)
            ):
                raise InvalidIdentityFieldTypeError(
                    cls.__name__, field_name, getattr(field_type, "__name__", str(field_type))
                )
            cls.__entity_id_field_name__ = field_name
            return

        for parent in cls.__mro__[1:]:
            if hasattr(parent, "__entity_id_field_name__"):
                cls.__entity_id_field_name__ = parent.__entity_id_field_name__
                return

        raise NoEntityIdException(cls.__name__)

    @property
    @inherit_context
    def __entity_id__(self) -> EntityId:
        return getattr(self, type(self).__entity_id_field_name__)

    @inherit_context
    def _can_mutate(self) -> bool:
        return self.can_mutate()

    @inherit_context
    def can_mutate(self) -> bool:
        return True

    def __eq__(self, other: Any) -> bool:
        if type(self) is not type(other):
            return False
        return self.__entity_id__ == other.__entity_id__

    def __hash__(self) -> int:
        return hash(self.__entity_id__)


class RootEntity(Entity):
    pass
