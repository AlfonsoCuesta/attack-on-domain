from __future__ import annotations

from typing import Generic, TypeVar, cast

from aod._internal.application.repository import Command, Query
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases
from aod._internal.infrastructure.handlers.async_ import CommandHandler, QueryHandler
from aod._internal.type_checks.handler_checks_async import (
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
        q_type = extract_handler_type(h)
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
            msg = f"Duplicate handler for {q_type.__name__}"
            raise DomainException(msg)
        handlers[q_type] = h

    async def command(self, command: Command[TEntity, TResult]) -> TResult:
        handler = self._commands.get(type(command))
        if handler is None:
            msg = f"No command handler registered for {type(command).__name__}"
            raise DomainException(msg)
        return cast(TResult, await handler.handle(command))

    async def query(self, query: Query[TEntity, TResult]) -> TResult:
        handler = self._queries.get(type(query))
        if handler is None:
            msg = f"No query handler registered for {type(query).__name__}"
            raise DomainException(msg)
        return cast(TResult, await handler.handle(query))
