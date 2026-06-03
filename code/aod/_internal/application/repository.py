from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar, overload

from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.core.type_handlers.generic_utils import (
    get_generic_arg_from_mro,
    validate_generic_arg_is_subclass,
)
from aod._internal.domain.entity import RootEntity

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")


class Command(BaseSealed, Generic[TEntity, TResult]):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        validate_generic_arg_is_subclass(cls, Command, RootEntity, arg_name="TEntity")


class Query(BaseSealed, Generic[TEntity, TResult]):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        validate_generic_arg_is_subclass(cls, Query, RootEntity, arg_name="TEntity")


C = TypeVar("C", bound=Command)
Q = TypeVar("Q", bound=Query)


class CommandHandler(BaseSealed, Generic[C]):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        validate_generic_arg_is_subclass(cls, CommandHandler, Command)

    @abstractmethod
    def handle(self, cmd: C) -> TResult: ...


class QueryHandler(BaseSealed, Generic[Q]):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        validate_generic_arg_is_subclass(cls, QueryHandler, Query)

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
            self._add_handler(h, CommandHandler, self._commands)

        for h in self.query_handlers:
            self._add_handler(h, QueryHandler, self._queries)

    def _add_handler(
        self,
        h: CommandHandler | QueryHandler,
        handler_type: type[CommandHandler | QueryHandler],
        handlers: dict,
    ) -> None:
        self._check_handler(h, handler_type)
        q_type = _extract_handler_type(h)
        if q_type in handlers:
            msg = f"Duplicate handler for {q_type.__name__}"
            raise DomainException(msg)
        handlers[q_type] = h

    def _check_handler(
        self, h: CommandHandler | QueryHandler, handler_type: type[CommandHandler | QueryHandler]
    ) -> None:
        if not issubclass(type(h), handler_type):
            msg = f"Handler {type(h).__name__} does not handle a {handler_type.__name__}"
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
    t = get_generic_arg_from_mro(type(handler), (CommandHandler, QueryHandler))
    if isinstance(t, type) and issubclass(t, (Command, Query)):
        return t
    msg = f"Cannot determine Command/Query type for {type(handler).__name__}"
    raise DomainException(msg)
