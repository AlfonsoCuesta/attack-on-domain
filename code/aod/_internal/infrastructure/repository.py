from __future__ import annotations

from typing import Generic, TypeVar

from aod._internal.application.contracts import Command, Projection, Query
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases
from aod._internal.infrastructure.handlers import (
    CommandHandler,
    ProjectionHandler,
    QueryHandler,
    _extract_handler_type,
)

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")


class Repository(BaseSealed, Generic[TEntity]):
    command_handlers: list[CommandHandler] = Field(default_factory=list)
    query_handlers: list[QueryHandler] = Field(default_factory=list)
    projection_handlers: list[ProjectionHandler] = Field(default_factory=list)
    _commands: dict[type[Command], CommandHandler] = PrivateField(default_factory=dict)
    _queries: dict[type[Query], QueryHandler] = PrivateField(default_factory=dict)
    _projections: dict[type[Projection], ProjectionHandler] = PrivateField(default_factory=dict)

    def __post_init__(self) -> None:
        for h in self.command_handlers:
            self._add_handler(h, CommandHandler, self._commands)

        for h in self.query_handlers:
            self._add_handler(h, QueryHandler, self._queries)

        for h in self.projection_handlers:
            self._add_handler(h, ProjectionHandler, self._projections)

    def _add_handler(
        self,
        h: CommandHandler | QueryHandler | ProjectionHandler,
        handler_type: type[CommandHandler | QueryHandler | ProjectionHandler],
        handlers: dict,
    ) -> None:
        self._check_handler(h, handler_type)
        q_type = _extract_handler_type(h)

        if handler_type is not ProjectionHandler:
            assert isinstance(h, (CommandHandler, QueryHandler))
            self._validate_handler_entity(h, q_type)  # type: ignore

        if q_type in handlers:
            msg = f"Duplicate handler for {q_type.__name__}"
            raise DomainException(msg)
        handlers[q_type] = h

    def _validate_handler_entity(
        self,
        h: CommandHandler | QueryHandler,
        cmd_or_query_type: type[Command | Query],
    ) -> None:
        handler_entity = get_generic_arg_from_orig_bases(cmd_or_query_type, Command)
        if handler_entity is None:
            handler_entity = get_generic_arg_from_orig_bases(cmd_or_query_type, Query)
        repo_entity = get_generic_arg_from_orig_bases(type(self), Repository)
        if (
            isinstance(handler_entity, type)
            and isinstance(repo_entity, type)
            and handler_entity is not repo_entity
        ):
            msg = f"Handler {type(h).__name__} handles entity {handler_entity.__name__}, but repository is for entity {repo_entity.__name__}"
            raise DomainException(msg)

    def _check_handler(
        self,
        h: CommandHandler | QueryHandler | ProjectionHandler,
        handler_type: type[CommandHandler | QueryHandler | ProjectionHandler],
    ) -> None:
        if not issubclass(type(h), handler_type):
            msg = f"Handler {type(h).__name__} does not handle a {handler_type.__name__}"
            raise DomainException(msg)

    def command(self, cmd: Command[TEntity, TResult]) -> TResult:
        handler = self._commands.get(type(cmd))
        if handler is None:
            msg = f"No command handler registered for {type(cmd).__name__}"
            raise DomainException(msg)
        return handler.handle(cmd)  # type: ignore

    def query(self, query: Query[TEntity, TResult]) -> TResult:
        handler = self._queries.get(type(query))
        if handler is None:
            msg = f"No query handler registered for {type(query).__name__}"
            raise DomainException(msg)
        return handler.handle(query)  # type: ignore

    def projection(self, projection: Projection[TResult]) -> TResult:
        handler = self._projections.get(type(projection))
        if handler is None:
            msg = f"No projection handler registered for {type(projection).__name__}"
            raise DomainException(msg)
        return handler.handle(projection)  # type: ignore
