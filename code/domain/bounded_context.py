from __future__ import annotations

from typing import Iterable, Optional, TypeAlias

from .entity import Entity, RootEntity
from .service import Service

RootEntityType: TypeAlias = type[RootEntity]
ServiceType: TypeAlias = type[Service]


class BoundedContext:
    """
    A bounded context defined by its aggregate roots.

    This class expects a collection of *entity classes*, not instances.
    """

    def __init__(
        self,
        aggregate_roots: Optional[Iterable[RootEntityType]] = None,
        services: Optional[Iterable[ServiceType]] = None,
    ):
        if aggregate_roots is None:
            aggregate_roots = []
        if services is None:
            services = []

        for item in aggregate_roots:
            if not issubclass(item, Entity):
                raise ValueError(f"{item.__name__} is not an Entity")
            if not item.is_root():
                raise ValueError(f"{item.__name__} is not a root Entity")

        for service in services:
            if not issubclass(service, Service):
                raise TypeError(f"{service.__name__} is not a Service")

        self.aggregate_roots: tuple[RootEntityType, ...] = tuple(
            aggregate_roots
        )
        self.services: tuple[ServiceType, ...] = tuple(services)
