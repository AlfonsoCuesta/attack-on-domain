from __future__ import annotations

from typing import Any, get_type_hints

from aod._internal.core.base_guarded import BaseGuarded, inherit_context
from aod._internal.core.domain_exception import NoEntityIdException, TooManyEntityIdsException
from aod._internal.core.event_emitter import EventEmitter
from aod._internal.core.fields.fields import PrivateField
from aod._internal.core.reconstructable import ReconstructMixin
from aod._internal.domain.entity_id import EntityId


class Entity(ReconstructMixin, BaseGuarded):
    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__name__ in ("RootEntity"):
            return
        hints = get_type_hints(cls)
        eid_fields = [
            name
            for name, tp in hints.items()
            if isinstance(tp, type) and tp is not EntityId and issubclass(tp, EntityId)
        ]
        if not eid_fields:
            raise NoEntityIdException(cls.__name__)
        if len(eid_fields) > 1:
            raise TooManyEntityIdsException(cls.__name__)
        cls.__entity_id_field_name__ = eid_fields[0]

    @property
    @inherit_context
    def __entity_id__(self) -> EntityId:
        return getattr(self, type(self).__entity_id_field_name__)

    def __eq__(self, other: Any) -> bool:
        if type(self) is not type(other):
            return False
        return self.__entity_id__ == other.__entity_id__

    def __hash__(self) -> int:
        return hash(self.__entity_id__)


class RootEntity(Entity):
    pass
