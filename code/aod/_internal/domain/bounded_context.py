from __future__ import annotations

from collections.abc import Iterable

from aod._internal.core.domain_exception import (
    ClassExpectedError,
    InvalidEntityTypeError,
    InvalidRootEntityTypeError,
    InvalidServiceTypeError,
)
from aod._internal.core.type_handlers import BaseGuardedTypeHandler, ServiceTypeHandler

from .describe import TypeDoc, describe
from .entity import Entity, RootEntity
from .service import Service
from .value_object import ValueObject

type RootEntityType = type[RootEntity]
type EntityType = type[Entity]
type ValueObjectType = type[ValueObject]
type ServiceType = type[Service]


class BoundedContext:
    def __init__(
        self,
        aggregate_roots: Iterable[RootEntityType] | None = None,
        services: Iterable[ServiceType] | None = None,
        *,
        name: str | None = None,
    ):
        aggregate_roots, services = self._validate_parameters(aggregate_roots, services)
        discovered_entities, discovered_vos = self._discover_and_check(aggregate_roots, services)

        self.name: str | None = name
        self.aggregate_roots: tuple[RootEntityType, ...] = tuple(aggregate_roots)
        self.services: tuple[ServiceType, ...] = tuple(services)
        self.entities: tuple[EntityType, ...] = tuple(discovered_entities)
        self.value_objects: tuple[ValueObjectType, ...] = tuple(discovered_vos)

    def _validate_parameters(
        self,
        aggregate_roots: Iterable[RootEntityType] | None,
        services: Iterable[ServiceType] | None,
    ) -> tuple[list[RootEntityType], list[ServiceType]]:
        if aggregate_roots is None:
            aggregate_roots = []
        if services is None:
            services = []

        for item in aggregate_roots:
            if not isinstance(item, type):
                raise ClassExpectedError(role="aggregate root", got=item)
            if not issubclass(item, Entity):
                raise InvalidEntityTypeError(item.__name__)
            if not issubclass(item, RootEntity):
                raise InvalidRootEntityTypeError(item.__name__)

        for service in services:
            if not isinstance(service, type):
                raise ClassExpectedError(role="service", got=service)
            if not issubclass(service, Service):
                raise InvalidServiceTypeError(service.__name__)

        return list(aggregate_roots), list(services)

    def _discover_and_check(
        self,
        aggregate_roots: list[RootEntityType],
        services: list[ServiceType],
    ) -> tuple[list[EntityType], list[ValueObjectType]]:
        discovered_entities, discovered_vos = BaseGuardedTypeHandler.discover_types(aggregate_roots)

        all_entities = list(aggregate_roots) + discovered_entities
        for entity_cls in all_entities:
            BaseGuardedTypeHandler.check_root_entity(entity_cls)

        for vo_cls in discovered_vos:
            BaseGuardedTypeHandler.check_value_object(vo_cls)

        for service_cls in services:
            ServiceTypeHandler.check_service(service_cls)

        return discovered_entities, discovered_vos

    def describe(self) -> list[TypeDoc]:
        result: list[TypeDoc] = []

        for root_cls in self.aggregate_roots:
            result.append(describe(root_cls, "RootEntity"))

        for ent_cls in self.entities:
            result.append(describe(ent_cls, "Entity"))

        for vo_cls in self.value_objects:
            result.append(describe(vo_cls, "ValueObject"))

        for svc_cls in self.services:
            result.append(describe(svc_cls, "Service"))

        return result

    def __repr__(self) -> str:
        return self.name or super().__repr__()
