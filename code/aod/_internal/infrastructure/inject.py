from __future__ import annotations

from functools import partial
from typing import Any, Callable, get_origin

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.handler.handler import HandlerProtocol
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.application.port import Port
from aod._internal.application.unit_of_work import UnitOfWork
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.infrastructure_exception import PortNotFoundError
from aod._internal.infrastructure.container import AdapterContainerBase
from aod._internal.infrastructure.projection import ProjectionBase

_SPECIAL_TYPES = (
    UnitOfWork,
    AsyncLogger,
    Logger,
    AsyncEventBus,
    EventBus,
    AsyncCache,
    Cache,
)


def _is_special_type(tp: object) -> bool:
    return isinstance(tp, type) and issubclass(tp, _SPECIAL_TYPES)


def _extract_port_type(tp: object) -> type[Port] | None:
    origin = get_origin(tp)
    if origin is not None:
        tp = origin
    if isinstance(tp, type) and issubclass(tp, Port) and not issubclass(tp, HandlerProtocol):
        return tp
    return None


def _inject_use_case(
    container: AdapterContainerBase,
    operation_cls: type[UseCase | AsyncUseCase],
) -> dict[str, Any]:
    return {"uow": container.get_uow()}


def _inject_ports(
    container: AdapterContainerBase,
    operation_cls: type[BaseOperation],
    kwargs: dict[str, Any],
) -> None:
    for field_name, field_info in operation_cls.__model_fields__.items():
        if field_name.startswith("_"):
            continue
        field_type = field_info.annotation
        if field_type is None or _is_special_type(field_type):
            continue
        port_type = _extract_port_type(field_type)
        if port_type is not None:
            port_value = container.get_port(port_type)
            if port_value is None:
                raise PortNotFoundError(port_type)
            kwargs[field_name] = port_value


def inject_projection(
    container: AdapterContainerBase,
    operation_cls: type[ProjectionBase],
) -> dict[str, Any]:
    session_field = operation_cls.__model_fields__.get("session")
    if session_field is None:
        return {"session": None}

    session_type = session_field.annotation
    if isinstance(session_type, type) and issubclass(session_type, type(None)):
        return {"session": None}

    return {"session": container.get_session(session_type)}


def inject_adapters(
    container: AdapterContainerBase,
    operation_cls: type[UseCase] | type[AsyncUseCase] | type[ProjectionBase],
    **overrides: Any,
) -> Callable:
    if overrides:
        container = container.copy(**overrides)

    kwargs: dict[str, Any] = {
        "logger": container.logger,
        "event_bus": container.event_bus,
        "cache": container.cache,
    }

    if issubclass(operation_cls, ProjectionBase):
        kwargs.update(inject_projection(container, operation_cls))
    elif issubclass(operation_cls, (UseCase, AsyncUseCase)):
        kwargs.update(_inject_use_case(container, operation_cls))

    _inject_ports(container, operation_cls, kwargs)

    return partial(operation_cls, **kwargs)
