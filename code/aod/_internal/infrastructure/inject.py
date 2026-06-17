from __future__ import annotations

from typing import Any, get_origin

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.handler.handler import HandlerProtocol
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.application.port import Port
from aod._internal.application.unit_of_work import UnitOfWork
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.core.base_operation import BaseOperation
from aod._internal.infrastructure.container import AdapterContainerBase
from aod._internal.infrastructure.projection import ProjectionBase

SPECIAL_TYPES = (
    UnitOfWork,
    AsyncLogger,
    Logger,
    AsyncEventBus,
    EventBus,
    AsyncCache,
    Cache,
)


def is_special_type(tp: object) -> bool:
    return isinstance(tp, type) and issubclass(tp, SPECIAL_TYPES)


def extract_port_type(tp: object) -> type[Port] | None:
    origin = get_origin(tp)
    if origin is not None:
        tp = origin
    if isinstance(tp, type) and issubclass(tp, Port) and not issubclass(tp, HandlerProtocol):
        return tp
    return None


def inject_use_case(
    container: AdapterContainerBase,
    operation_cls: type[UseCase | AsyncUseCase],
) -> dict[str, Any]:
    return {"uow": container.get_uow()}


def inject_ports(
    container: AdapterContainerBase,
    operation_cls: type[BaseOperation],
    kwargs: dict[str, Any],
) -> None:
    for field_name, field_info in operation_cls.__model_fields__.items():
        field_type = field_info.annotation
        if field_type is None or is_special_type(field_type):
            continue
        port_type = extract_port_type(field_type)
        if port_type is not None:
            port_value = container.get_port(port_type)
            kwargs[field_name] = port_value


def inject_projection(
    container: AdapterContainerBase,
    operation_cls: type[ProjectionBase],
) -> dict[str, Any]:
    session_type = operation_cls.__model_fields__["session"].annotation
    return {"session": container.get_session(session_type)}


TOperationBases = UseCase | AsyncUseCase | ProjectionBase


def inject_adapters(
    container: AdapterContainerBase,
    operation_cls: type[TOperationBases],
    **overrides: Any,
) -> TOperationBases:
    if overrides:
        container = container.copy(**overrides)

    kwargs: dict[str, Any] = {
        "logger": container.logger,
        "event_bus": container.event_bus,
        "cache": container.cache,
    }

    inject_ports(container, operation_cls, kwargs)
    if issubclass(operation_cls, ProjectionBase):
        kwargs.update(inject_projection(container, operation_cls))
    elif issubclass(operation_cls, (UseCase, AsyncUseCase)):
        kwargs.update(inject_use_case(container, operation_cls))

    return operation_cls(**kwargs)
