from __future__ import annotations

from types import UnionType
from typing import TypeVar, Union, get_args, get_origin

from aod._internal.application.handler.handler import HandlerProtocol
from aod._internal.application.port import Port
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.infrastructure.handlers import (
    AsyncCommandHandler,
    AsyncQueryHandler,
    CommandHandler,
    QueryHandler,
)
from aod._internal.infrastructure.projection import ProjectionBase
from aod._internal.infrastructure.session import AsyncSession, Session

_SYNC_HANDLERS = CommandHandler | QueryHandler
_ASYNC_HANDLERS = AsyncCommandHandler | AsyncQueryHandler

AnyHandler = (
    type[CommandHandler] | type[QueryHandler] | type[AsyncCommandHandler] | type[AsyncQueryHandler]
)

TUseCase = TypeVar("TUseCase", bound=UseCase | AsyncUseCase)
TProjection = TypeVar("TProjection", bound=ProjectionBase)
TOperation = TypeVar("TOperation", bound=UseCase | AsyncUseCase | ProjectionBase)


def _is_port_type(tp: object) -> bool:
    origin = get_origin(tp)
    if origin is UnionType or origin is Union:
        return False
    if origin is not None:
        return any(isinstance(a, type) and issubclass(a, Port) for a in get_args(tp))
    return isinstance(tp, type) and issubclass(tp, Port)


def extract_port_type(tp: object) -> type[Port] | None:
    origin = get_origin(tp)
    if origin is not None:
        tp = origin
    if isinstance(tp, type) and issubclass(tp, Port) and not issubclass(tp, HandlerProtocol):
        return tp
    return None


def _is_session_annotation(tp: object) -> bool:
    return isinstance(tp, type) and issubclass(tp, (Session, AsyncSession))
