from __future__ import annotations

from typing import ClassVar

from aod._internal.core.base_mutable import BaseMutable, MutableBaseMeta
from aod._internal.core.event_emitter import EventEmitter


class EntityMeta(MutableBaseMeta):
    def __new__(mcls, name, bases, namespace, root=None):
        cls = super().__new__(mcls, name, bases, namespace)
        if root is not None:
            cls.__aggregate_root__ = bool(root)
        return cls


class Entity(BaseMutable, metaclass=EntityMeta):
    __aggregate_root__: ClassVar[bool] = False

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        object.__setattr__(self, "_event_emitter", EventEmitter())

    @classmethod
    def is_root(cls) -> bool:
        return cls.__aggregate_root__


class RootEntity(Entity, root=True):
    pass
