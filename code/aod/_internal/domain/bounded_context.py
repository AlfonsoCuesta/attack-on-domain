from __future__ import annotations

import typing
from typing import Iterable, Optional, TypeAlias

from aod._internal.core.domain_exception import (
    ClassExpectedError,
    InvalidEntityTypeError,
    InvalidRootEntityTypeError,
    InvalidServiceTypeError,
)
from aod._internal.core.type_checking import (
    check_entity,
    check_root_entity,
    check_service,
    check_value_object,
    extract_types_from_annotation,
)

from .entity import Entity, RootEntity
from .service import Service
from .value_object import ValueObject

RootEntityType: TypeAlias = type[RootEntity]
EntityType: TypeAlias = type[Entity]
ValueObjectType: TypeAlias = type[ValueObject]
ServiceType: TypeAlias = type[Service]


def _discover_types(
    root_entities: list[type[Entity]],
) -> tuple[list[type[Entity]], list[type[ValueObject]]]:
    entities: set[type[Entity]] = set()
    vos: set[type[ValueObject]] = set()
    seen: set[type] = set()
    pending: list[type] = list(root_entities)

    while pending:
        cls = pending.pop()
        if cls in seen:
            continue
        seen.add(cls)

        try:
            hints = typing.get_type_hints(cls)
        except Exception:
            continue

        for field_name, field_type in hints.items():
            if field_name.startswith("_"):
                continue
            for t in extract_types_from_annotation(field_type):
                if not isinstance(t, type):
                    continue
                if (
                    issubclass(t, Entity)
                    and t is not Entity
                    and t not in root_entities
                    and t not in entities
                ):
                    entities.add(t)
                    pending.append(t)
                if issubclass(t, ValueObject) and t is not ValueObject and t not in vos:
                    vos.add(t)
                    pending.append(t)

    return list(entities), list(vos)


class BoundedContext:
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

        discovered_entities, discovered_vos = _discover_types(list(aggregate_roots))

        all_entities = list(aggregate_roots) + discovered_entities
        for entity_cls in all_entities:
            check_root_entity(entity_cls)

        for vo_cls in discovered_vos:
            check_value_object(vo_cls)

        for service_cls in services:
            check_service(service_cls)

        self.aggregate_roots: tuple[RootEntityType, ...] = tuple(aggregate_roots)
        self.services: tuple[ServiceType, ...] = tuple(services)
        self.entities: tuple[EntityType, ...] = tuple(discovered_entities)
        self.value_objects: tuple[ValueObjectType, ...] = tuple(discovered_vos)
