from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar, get_args, get_origin, overload

from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.fields.fields import Field, PrivateField

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")


class Command(BaseSealed, Generic[TEntity, TResult]): ...


class Query(BaseSealed, Generic[TEntity, TResult]): ...


C = TypeVar("C", bound=Command)
Q = TypeVar("Q", bound=Query)


class CommandHandler(BaseSealed, Generic[C]):
    @abstractmethod
    def handle(self, cmd: C) -> TResult: ...


class QueryHandler(BaseSealed, Generic[Q]):
    @abstractmethod
    def handle(self, query: Q) -> TResult: ...


class Repository(BaseSealed, Generic[TEntity]): ...


class RepositoryCQRS(BaseSealed, Generic[TEntity]):
    command_handlers: list[CommandHandler] = Field(default_factory=list)
    query_handlers: list[QueryHandler] = Field(default_factory=list)
    _commands: dict[type[Command], CommandHandler] = PrivateField(default_factory=dict)
    _queries: dict[type[Query], QueryHandler] = PrivateField(default_factory=dict)

    def __post_init__(self) -> None:
        for h in self.command_handlers:
            self._check_handler(h, CommandHandler, Command)
            cmd_type = _extract_handler_type(h)
            if cmd_type in self._commands:
                msg = f"Duplicate command handler for {cmd_type.__name__}"
                raise DomainException(msg)
            self._commands[cmd_type] = h

        for h in self.query_handlers:
            self._check_handler(h, QueryHandler, Query)
            q_type = _extract_handler_type(h)
            if q_type in self._queries:
                msg = f"Duplicate query handler for {q_type.__name__}"
                raise DomainException(msg)
            self._queries[q_type] = h

    def _check_handler(
        self,
        h: CommandHandler | QueryHandler,
        handler_type: type[CommandHandler | QueryHandler],
        subclass: type[Query | Command],
    ) -> None:
        if not issubclass(type(h), handler_type):
            msg = f"Handler {type(h).__name__} does not handle a {handler_type.__name__}"
            raise DomainException(msg)
        q_type = _extract_handler_type(h)
        if not issubclass(q_type, subclass):
            msg = f"Handler {type(h).__name__} does not handle a {subclass.__name__}"
            raise DomainException(msg)

    def command(self, cmd: Command[TEntity, TResult]) -> TResult:
        handler = self._commands.get(type(cmd))
        if handler is None:
            msg = f"No command handler registered for {type(cmd).__name__}"
            raise DomainException(msg)
        return handler.handle(cmd)

    def query(self, query: Query[TEntity, TResult]) -> TResult:
        handler = self._queries.get(type(query))
        if handler is None:
            msg = f"No query handler registered for {type(query).__name__}"
            raise DomainException(msg)
        return handler.handle(query)


@overload
def _extract_handler_type(handler: CommandHandler) -> type[Command]: ...


@overload
def _extract_handler_type(handler: QueryHandler) -> type[Query]: ...


def _extract_handler_type(handler: CommandHandler | QueryHandler) -> type[Command | Query]:
    for base in type(handler).__mro__:
        for orig_base in getattr(base, "__orig_bases__", []):
            origin = get_origin(orig_base)
            if origin is CommandHandler or origin is QueryHandler:
                t = get_args(orig_base)[0]
                if isinstance(t, type) and issubclass(t, (Command, Query)):
                    return t
    msg = f"Cannot determine Command/Query type for {type(handler).__name__}"
    raise DomainException(msg)
