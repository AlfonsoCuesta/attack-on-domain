from __future__ import annotations

from functools import partial
from typing import Any, get_args, get_origin, get_type_hints

from aod._internal.application.contracts import Command, Query
from aod._internal.application.port import Port
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.infrastructure.container import AdapterContainerBase
from aod._internal.infrastructure.handlers.handlers import (
    AsyncCommandHandler,
    AsyncQueryHandler,
    CommandHandler,
    QueryHandler,
)
from aod._internal.infrastructure.projection import ProjectionBase

_SPECIAL_FIELDS = frozenset({"uow", "logger", "event_bus", "cache"})


def _extract_port_type(tp: object) -> type[Port] | None:
    if isinstance(tp, type) and issubclass(tp, Port):
        return tp
    return None


def _extract_handler_contract(tp: object) -> type[Command] | type[Query] | None:
    if not isinstance(tp, type):
        return None
    if not issubclass(tp, (CommandHandler, AsyncCommandHandler, QueryHandler, AsyncQueryHandler)):
        return None
    for base in getattr(tp, "__orig_bases__", ()):
        base_origin = get_origin(base)
        if base_origin in (CommandHandler, AsyncCommandHandler, QueryHandler, AsyncQueryHandler):
            args = get_args(base)
            if args:
                first = args[0]
                if isinstance(first, type) and issubclass(first, (Command, Query)):
                    return first
    return None


def _pick_session(container: AdapterContainerBase) -> Any:
    for s in container.sessions:
        return s
    return None


def inject_adapters(
    container: AdapterContainerBase,
    operation_cls: type[UseCase | AsyncUseCase | ProjectionBase],
    **overrides: Any,
) -> partial:
    if overrides:
        container = container.copy(**overrides)

    kwargs: dict[str, Any] = {
        "logger": container.logger,
        "event_bus": container.event_bus,
        "cache": container.cache,
    }

    if issubclass(operation_cls, ProjectionBase):
        kwargs["session"] = _pick_session(container)
        return partial(operation_cls, **kwargs)

    kwargs["uow"] = container.get_uow()
    hints = get_type_hints(operation_cls)

    for field_name in operation_cls.__model_fields__:
        if field_name.startswith("_") or field_name in _SPECIAL_FIELDS:
            continue
        field_type = hints.get(field_name)
        if field_type is None:
            continue

        port_type = _extract_port_type(field_type)
        if port_type is not None:
            kwargs[field_name] = container.get_port(port_type)
            continue

        handler_contract = _extract_handler_contract(field_type)
        if handler_contract is not None:
            kwargs[field_name] = container.get_handler(handler_contract)
            continue

    return partial(operation_cls, **kwargs)
