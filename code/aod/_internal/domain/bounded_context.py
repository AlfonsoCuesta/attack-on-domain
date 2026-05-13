from __future__ import annotations

from typing import Iterable, Optional, TypeAlias

from aod._internal.core.domain_exception import (
    ClassExpectedError,
    InvalidEntityTypeError,
    InvalidRootEntityTypeError,
    InvalidServiceTypeError,
)

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
            if not isinstance(item, type):
                raise ClassExpectedError(role="aggregate root", got=item)
            if not issubclass(item, Entity):
                raise InvalidEntityTypeError(item.__name__)
            if not item.is_root():
                raise InvalidRootEntityTypeError(item.__name__)

        for service in services:
            if not isinstance(service, type):
                raise ClassExpectedError(role="service", got=service)
            if not issubclass(service, Service):
                raise InvalidServiceTypeError(service.__name__)

        self.aggregate_roots: tuple[RootEntityType, ...] = tuple(
            aggregate_roots
        )
        self.services: tuple[ServiceType, ...] = tuple(services)
