from __future__ import annotations

from collections.abc import Iterable

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.contracts import Command, Query
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.handler import (
    AsyncCommandPort,
    AsyncQueryPort,
    CommandPort,
    QueryPort,
)
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.application.port import Port
from aod._internal.application.unit_of_work import AsyncUnitOfWork, UnitOfWork
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.core.domain_exception import (
    ClassExpectedError,
    InvalidEntityTypeError,
    InvalidRootEntityTypeError,
    InvalidServiceTypeError,
)
from aod._internal.core.type_handlers import BaseGuardedTypeHandler, ServiceTypeHandler
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.service import Service
from aod._internal.domain.value_object import ValueObject

_INTERNAL_PORT_TYPES = frozenset(
    {UnitOfWork, AsyncUnitOfWork, Logger, AsyncLogger, EventBus, AsyncEventBus, Cache, AsyncCache}
)

type RootEntityType = type[RootEntity]
type EntityType = type[Entity]
type ValueObjectType = type[ValueObject]
type ServiceType = type[Service]
type UseCaseType = type[UseCase] | type[AsyncUseCase]
type ContractType = type[Command] | type[Query]
type PortType = type[Port]


class BoundedContext:
    def __init__(
        self,
        aggregate_roots: Iterable[RootEntityType] | None = None,
        services: Iterable[ServiceType] | None = None,
        use_cases: Iterable[UseCaseType] | None = None,
        *,
        name: str | None = None,
    ):
        aggregate_roots, services, use_cases = self._validate_parameters(
            aggregate_roots, services, use_cases
        )
        discovered_entities, discovered_vos = self._discover_and_check(aggregate_roots, services)
        contracts, ports = self._extract_from_use_cases(use_cases, aggregate_roots)
        contracts_by_root = self._group_contracts_by_root(contracts, aggregate_roots)

        self.name: str | None = name
        self.aggregate_roots: tuple[RootEntityType, ...] = tuple(aggregate_roots)
        self.services: tuple[ServiceType, ...] = tuple(services)
        self.use_cases: tuple[UseCaseType, ...] = tuple(use_cases)
        self.entities: tuple[EntityType, ...] = tuple(discovered_entities)
        self.value_objects: tuple[ValueObjectType, ...] = tuple(discovered_vos)
        self.contracts: tuple[ContractType, ...] = tuple(contracts)
        self.ports: tuple[PortType, ...] = tuple(ports)
        self.contracts_by_root: dict[RootEntityType, list[ContractType]] = contracts_by_root

    def _validate_parameters(
        self,
        aggregate_roots: Iterable[RootEntityType] | None,
        services: Iterable[ServiceType] | None,
        use_cases: Iterable[UseCaseType] | None,
    ) -> tuple[list[RootEntityType], list[ServiceType], list[UseCaseType]]:
        if aggregate_roots is None:
            aggregate_roots = []
        if services is None:
            services = []
        if use_cases is None:
            use_cases = []

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

        for uc in use_cases:
            if not isinstance(uc, type):
                raise ClassExpectedError(role="use case", got=uc)
            if not issubclass(uc, (UseCase, AsyncUseCase)):
                raise InvalidServiceTypeError(uc.__name__)

        return list(aggregate_roots), list(services), list(use_cases)

    def _discover_and_check(
        self,
        aggregate_roots: list[RootEntityType],
        services: list[ServiceType],
    ) -> tuple[list[EntityType], list[ValueObjectType]]:
        discovered_entities, discovered_vos = BaseGuardedTypeHandler.discover_types(aggregate_roots)

        for entity_cls in list(aggregate_roots) + discovered_entities:
            BaseGuardedTypeHandler.check_root_entity(entity_cls)

        for vo_cls in discovered_vos:
            BaseGuardedTypeHandler.check_value_object(vo_cls)

        for service_cls in services:
            ServiceTypeHandler.check_service(service_cls)

        return discovered_entities, discovered_vos

    def _extract_from_use_cases(
        self,
        use_cases: list[UseCaseType],
        aggregate_roots: list[RootEntityType],
    ) -> tuple[list[ContractType], list[PortType]]:
        contracts: list[ContractType] = []
        ports: list[PortType] = []

        for uc in use_cases:
            for field_name in uc.__model_fields__:
                if field_name.startswith("_"):
                    continue
                field_type = uc.__model_fields__[field_name].annotation
                origin = getattr(field_type, "__origin__", None)
                if origin is not None and issubclass(
                    origin, (CommandPort, QueryPort, AsyncCommandPort, AsyncQueryPort)
                ):
                    args = getattr(field_type, "__args__", ())
                    if args and isinstance(args[0], type):
                        contracts.append(args[0])
                elif isinstance(field_type, type) and issubclass(field_type, Port):
                    if field_type not in _INTERNAL_PORT_TYPES:
                        ports.append(field_type)

        return contracts, ports

    @staticmethod
    def _group_contracts_by_root(
        contracts: list[ContractType],
        aggregate_roots: list[RootEntityType],
    ) -> dict[RootEntityType, list[ContractType]]:
        result: dict[RootEntityType, list[ContractType]] = {root: [] for root in aggregate_roots}

        for contract in contracts:
            for base in getattr(contract, "__orig_bases__", ()):
                origin = getattr(base, "__origin__", None)
                if origin is not None and issubclass(origin, (Command, Query)):
                    args = getattr(base, "__args__", ())
                    if args:
                        entity = args[0]
                        if entity in result:
                            result[entity].append(contract)

        return result

    def __repr__(self) -> str:
        return self.name or super().__repr__()
