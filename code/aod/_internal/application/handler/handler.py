from typing import Generic, Protocol, TypeVar

from aod._internal.application.contracts import Command, Query

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")
TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)


class CommandHandler(Protocol, Generic[TCommand]):
    def handle(self, command: Command[TEntity, TResult]) -> TResult: ...


class QueryHandler(Protocol, Generic[TQuery]):
    def handle(self, query: Query[TEntity, TResult]) -> TResult: ...


class AsyncCommandHandler(Protocol, Generic[TCommand]):
    async def handle(self, command: Command[TEntity, TResult]) -> TResult: ...


class AsyncQueryHandler(Protocol, Generic[TQuery]):
    async def handle(self, query: Query[TEntity, TResult]) -> TResult: ...
