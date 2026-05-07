from __future__ import annotations

from typing import Iterable, TypeAlias

from .entity import Entity, RootEntity

RootEntityType: TypeAlias = type[RootEntity]
AnyEntityType: TypeAlias = type[Entity]


class BoundedContext:
    """
    A bounded context defined by its aggregate roots.

    This class expects a collection of *entity classes*, not instances.
    """

    def __init__(self, roots: Iterable[AnyEntityType]):
        roots_t = tuple(roots)
        for entity in roots_t:
            if not issubclass(entity, Entity):
                raise TypeError(f"{entity!r} is not an Entity")
            if not entity.is_root():
                raise ValueError(
                    f"{entity.__name__} is not a root Entity (root=True)"
                )
        self.aggregate_roots: tuple[AnyEntityType, ...] = roots_t
