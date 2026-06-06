from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar, cast

from aod._internal.application.projection import ProjectionCommand, ProjectionQuery, ReadModel
from aod._internal.core.async_utils import should_await
from aod._internal.core.domain_exception import ApplicationException
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.infrastructure.handlers.base_handler import AsyncBaseHandler

from .projection_handler import ProjectionCommandHandler as SyncProjectionCommandHandler
from .projection_handler import ProjectionQueryHandler as SyncProjectionQueryHandler
from .projection_store import _BaseProjectionStore

PQ = TypeVar("PQ", bound=ProjectionQuery)
PC = TypeVar("PC", bound=ProjectionCommand)
T = TypeVar("T", bound=ReadModel | None)


class ProjectionQueryHandler(AsyncBaseHandler, Generic[PQ]):
    @abstractmethod
    async def handle(self, query: PQ) -> object: ...


class ProjectionCommandHandler(AsyncBaseHandler, Generic[PC]):
    @abstractmethod
    async def handle(self, command: PC) -> object: ...


_Handler = (
    ProjectionQueryHandler
    | SyncProjectionQueryHandler
    | ProjectionCommandHandler
    | SyncProjectionCommandHandler
)


class ProjectionStore(_BaseProjectionStore):
    handlers: list[_Handler] = Field(default_factory=list)
    _query_handlers: dict[type, _Handler] = PrivateField(default_factory=dict)
    _command_handlers: dict[type, _Handler] = PrivateField(default_factory=dict)
    __allowed_handler_types__ = (
        ProjectionQueryHandler,
        SyncProjectionQueryHandler,
        ProjectionCommandHandler,
        SyncProjectionCommandHandler,
    )

    async def query(self, query: ProjectionQuery[T]) -> T:
        handler = self._query_handlers.get(type(query))
        if handler is None:
            msg = f"No handler registered for {type(query).__name__}"
            raise ApplicationException(msg)
        return cast(T, await should_await(handler.handle(query)))

    async def command(self, command: ProjectionCommand[T]) -> T:
        handler = self._command_handlers.get(type(command))
        if handler is None:
            msg = f"No handler registered for {type(command).__name__}"
            raise ApplicationException(msg)
        return cast(T, await should_await(handler.handle(command)))
