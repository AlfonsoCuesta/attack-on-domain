from __future__ import annotations

from typing import Any

from aod._internal.core.base_guarded import BaseGuarded, inherit_context
from aod._internal.core.domain_exception import NoEntityIdException, TooManyEntityIdsException
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
            cls.__entity_id_field_name__ = identity_fields[0]
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
