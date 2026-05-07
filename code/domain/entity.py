from __future__ import annotations

from typing import ClassVar

from core.base_mutable import BaseMutable, MutableBaseMeta


class EntityMeta(MutableBaseMeta):
    def __new__(mcls, name, bases, namespace, **kwargs):
        root = kwargs.pop("root", None)
        cls = super().__new__(mcls, name, bases, namespace)
        if root is not None:
            cls.__aggregate_root__ = bool(root)
        return cls


class Entity(BaseMutable, metaclass=EntityMeta):
    pass

    __aggregate_root__: ClassVar[bool] = False

    @classmethod
    def is_root(cls) -> bool:
        return bool(getattr(cls, "__aggregate_root__", False))


class RootEntity(Entity, root=True):
    pass
