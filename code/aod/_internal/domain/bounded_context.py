from __future__ import annotations

from typing import Iterable, Optional, TypeAlias

from aod._internal.core.domain_exception import (
    ClassExpectedError,
    InvalidEntityTypeError,
    InvalidRootEntityTypeError,
    InvalidServiceTypeError,
)
from aod._internal.core.type_handlers import BaseGuardedTypeHandler, ServiceTypeHandler
from aod._internal.domain.describers import BaseGuardedDescriber, ServiceDescriber

from .describe import TypeDoc
from .entity import Entity, RootEntity
from .service import Service
from .value_object import ValueObject

RootEntityType: TypeAlias = type[RootEntity]
EntityType: TypeAlias = type[Entity]
ValueObjectType: TypeAlias = type[ValueObject]
ServiceType: TypeAlias = type[Service]


class BoundedContext:
    def __init__(
        self,
        aggregate_roots: Optional[Iterable[RootEntityType]] = None,
        services: Optional[Iterable[ServiceType]] = None,
        *,
        name: str | None = None,
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

        discovered_entities, discovered_vos = BaseGuardedTypeHandler.discover_types(
            list(aggregate_roots)
        )

        all_entities = list(aggregate_roots) + discovered_entities
        for entity_cls in all_entities:
            BaseGuardedTypeHandler.check_root_entity(entity_cls)

        for vo_cls in discovered_vos:
            BaseGuardedTypeHandler.check_value_object(vo_cls)

        for service_cls in services:
            ServiceTypeHandler.check_service(service_cls)

        self.name: str | None = name
        self.aggregate_roots: tuple[RootEntityType, ...] = tuple(aggregate_roots)
        self.services: tuple[ServiceType, ...] = tuple(services)
        self.entities: tuple[EntityType, ...] = tuple(discovered_entities)
        self.value_objects: tuple[ValueObjectType, ...] = tuple(discovered_vos)

    def describe(self) -> list[TypeDoc]:
        result: list[TypeDoc] = []

        for root_cls in self.aggregate_roots:
            result.append(BaseGuardedDescriber.describe(root_cls, "RootEntity"))

        for ent_cls in self.entities:
            result.append(BaseGuardedDescriber.describe(ent_cls, "Entity"))

        for vo_cls in self.value_objects:
            result.append(BaseGuardedDescriber.describe(vo_cls, "ValueObject"))

        for svc_cls in self.services:
            result.append(ServiceDescriber.describe(svc_cls, "Service"))

        return result

    def __repr__(self) -> str:
        return self.name or super().__repr__()
