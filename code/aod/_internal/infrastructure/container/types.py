from __future__ import annotations

from typing import TypeVar, get_origin

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
from aod._internal.core.infrastructure_exception import AbstractSessionTypeError
from aod._internal.infrastructure.session import AsyncSession, Session

_SESSION_BASES = (Session, AsyncSession)

_SYNC_HANDLERS = CommandHandler | QueryHandler
_ASYNC_HANDLERS = AsyncCommandHandler | AsyncQueryHandler

AnyHandler = (
    type[CommandHandler] | type[QueryHandler] | type[AsyncCommandHandler] | type[AsyncQueryHandler]
)

TUseCase = TypeVar("TUseCase", bound=UseCase | AsyncUseCase)
TProjection = TypeVar("TProjection", bound=ProjectionBase)
TOperation = TypeVar("TOperation", bound=UseCase | AsyncUseCase | ProjectionBase)


def _is_port_type(tp: object) -> bool:
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


def _validate_concrete_session(field_name: str, field_type: object, owner_name: str) -> None:
    if isinstance(field_type, type) and field_type in _SESSION_BASES:
        raise AbstractSessionTypeError(owner_name, field_name, field_type)
