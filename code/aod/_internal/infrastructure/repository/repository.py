from __future__ import annotations

from typing import Generic, TypeVar, cast

from aod._internal.application.repository import Command, Query
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.infrastructure_exception import DuplicateHandlerError, HandlerNotFoundError
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases
from aod._internal.infrastructure.handlers import AsyncCommandHandler, AsyncQueryHandler, CommandHandler, QueryHandler
from aod._internal.type_checks.handler_checks import (
    extract_handler_type,
    validate_handler_entity,
    validate_handler_type,
)

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")


class Repository(BaseSealed, Generic[TEntity]):
    command_handlers: list[CommandHandler] = Field(default_factory=list)
    query_handlers: list[QueryHandler] = Field(default_factory=list)
    _commands: dict[type[Command], CommandHandler] = PrivateField(default_factory=dict)
    _queries: dict[type[Query], QueryHandler] = PrivateField(default_factory=dict)

    def __post_init__(self) -> None:
        for h in self.command_handlers:
            self._add_handler(h, CommandHandler, self._commands)

        for h in self.query_handlers:
            self._add_handler(h, QueryHandler, self._queries)

    def _add_handler(
        self,
        h: CommandHandler | QueryHandler,
        handler_type: type[CommandHandler] | type[QueryHandler],
        handlers: dict,
    ) -> None:
        validate_handler_type(h, handler_type)
        q_type = extract_handler_type(h, (CommandHandler, QueryHandler))
        repo_entity = get_generic_arg_from_orig_bases(type(self), Repository)
        validate_handler_entity(h, q_type, repo_entity)
        self._store(h, q_type, handlers)

    def _store(
        self,
        h: CommandHandler | QueryHandler,
        q_type: type[Command] | type[Query],
        handlers: dict,
    ) -> None:
        if q_type in handlers:
            raise DuplicateHandlerError(q_type.__name__)
        handlers[q_type] = h

    def command(self, command: Command[TEntity, TResult]) -> TResult:
        handler = self._commands.get(type(command))
        if handler is None:
            raise HandlerNotFoundError("command", type(command).__name__)
        return cast(TResult, handler.handle(command))

    def query(self, query: Query[TEntity, TResult]) -> TResult:
        handler = self._queries.get(type(query))
        if handler is None:
            raise HandlerNotFoundError("query", type(query).__name__)
        return cast(TResult, handler.handle(query))


class AsyncRepository(BaseSealed, Generic[TEntity]):
    command_handlers: list[AsyncCommandHandler] = Field(default_factory=list)
    query_handlers: list[AsyncQueryHandler] = Field(default_factory=list)
    _commands: dict[type[Command], AsyncCommandHandler] = PrivateField(default_factory=dict)
    _queries: dict[type[Query], AsyncQueryHandler] = PrivateField(default_factory=dict)

    def __post_init__(self) -> None:
        for h in self.command_handlers:
            self._add_handler(h, AsyncCommandHandler, self._commands)

        for h in self.query_handlers:
            self._add_handler(h, AsyncQueryHandler, self._queries)

    def _add_handler(
        self,
        h: AsyncCommandHandler | AsyncQueryHandler,
        handler_type: type[AsyncCommandHandler] | type[AsyncQueryHandler],
        handlers: dict,
    ) -> None:
        validate_handler_type(h, handler_type)
        q_type = extract_handler_type(h, (AsyncCommandHandler, AsyncQueryHandler))
        repo_entity = get_generic_arg_from_orig_bases(type(self), AsyncRepository)
        validate_handler_entity(h, q_type, repo_entity)
        self._store(h, q_type, handlers)

    def _store(
        self,
        h: AsyncCommandHandler | AsyncQueryHandler,
        q_type: type[Command] | type[Query],
        handlers: dict,
    ) -> None:
        if q_type in handlers:
            raise DuplicateHandlerError(q_type.__name__)
        handlers[q_type] = h

    async def command(self, command: Command[TEntity, TResult]) -> TResult:
        handler = self._commands.get(type(command))
        if handler is None:
            raise HandlerNotFoundError("command", type(command).__name__)
        return cast(TResult, await handler.handle(command))

    async def query(self, query: Query[TEntity, TResult]) -> TResult:
        handler = self._queries.get(type(query))
        if handler is None:
            raise HandlerNotFoundError("query", type(query).__name__)
        return cast(TResult, await handler.handle(query))
