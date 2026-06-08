from __future__ import annotations

from typing import Any, ClassVar, TypeVar, cast

from aod._internal.application.projection import ProjectionCommand, ProjectionQuery, ReadModel
from aod._internal.core.async_utils import should_await
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.infrastructure_exception import (
    DuplicateProjectionHandlerError,
    ProjectionHandlerNotFoundError,
    UnresolvableProjectionTypeError,
)
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_mro
from aod._internal.infrastructure.projection.projection_handler import (
    AsyncProjectionCommandHandler,
    AsyncProjectionQueryHandler,
    ProjectionCommandHandler,
    ProjectionQueryHandler,
)

T = TypeVar("T", bound=ReadModel | None)


class _BaseProjectionStore(BaseSealed):
    handlers: list[Any] = Field(default_factory=list)
    _query_handlers: dict[type, Any] = PrivateField(default_factory=dict)
    _command_handlers: dict[type, Any] = PrivateField(default_factory=dict)
    __allowed_handler_types__: ClassVar[tuple[type, ...]] = ()

    def _register_handler(self, h: Any) -> None:
        p_type = get_generic_arg_from_mro(type(h), self.__allowed_handler_types__)
        if not isinstance(p_type, type):
            raise UnresolvableProjectionTypeError(type(h).__name__)
        if issubclass(p_type, ProjectionQuery):
            if p_type in self._query_handlers:
                raise DuplicateProjectionHandlerError(p_type.__name__)
            self._query_handlers[p_type] = h
        elif issubclass(p_type, ProjectionCommand):
            if p_type in self._command_handlers:
                raise DuplicateProjectionHandlerError(p_type.__name__)
            self._command_handlers[p_type] = h

    def __post_init__(self) -> None:
        for h in self.handlers:
            self._register_handler(h)


class ProjectionStore(_BaseProjectionStore):
    handlers: list[ProjectionQueryHandler | ProjectionCommandHandler] = Field(default_factory=list)
    _query_handlers: dict[type, ProjectionQueryHandler] = PrivateField(default_factory=dict)
    _command_handlers: dict[type, ProjectionCommandHandler] = PrivateField(default_factory=dict)
    __allowed_handler_types__ = (ProjectionQueryHandler, ProjectionCommandHandler)

    def query(self, query: ProjectionQuery[T]) -> T:
        handler = self._query_handlers.get(type(query))
        if handler is None:
            raise ProjectionHandlerNotFoundError(type(query).__name__)
        return cast(T, handler.handle(query))

    def command(self, command: ProjectionCommand[T]) -> T:
        handler = self._command_handlers.get(type(command))
        if handler is None:
            raise ProjectionHandlerNotFoundError(type(command).__name__)
        return cast(T, handler.handle(command))


_Handler = (
    AsyncProjectionQueryHandler
    | ProjectionQueryHandler
    | AsyncProjectionCommandHandler
    | ProjectionCommandHandler
)


class AsyncProjectionStore(_BaseProjectionStore):
    handlers: list[_Handler] = Field(default_factory=list)
    _query_handlers: dict[type, _Handler] = PrivateField(default_factory=dict)
    _command_handlers: dict[type, _Handler] = PrivateField(default_factory=dict)
    __allowed_handler_types__ = (
        AsyncProjectionQueryHandler,
        ProjectionQueryHandler,
        AsyncProjectionCommandHandler,
        ProjectionCommandHandler,
    )

    async def query(self, query: ProjectionQuery[T]) -> T:
        handler = self._query_handlers.get(type(query))
        if handler is None:
            raise ProjectionHandlerNotFoundError(type(query).__name__)
        return cast(T, await should_await(handler.handle(query)))

    async def command(self, command: ProjectionCommand[T]) -> T:
        handler = self._command_handlers.get(type(command))
        if handler is None:
            raise ProjectionHandlerNotFoundError(type(command).__name__)
        return cast(T, await should_await(handler.handle(command)))
