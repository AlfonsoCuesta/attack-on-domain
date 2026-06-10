from abc import abstractmethod
from typing import Generic, TypeVar

from aod._internal.application.contracts import Command, Query
from aod._internal.application.port import Port

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")
TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)


class HandlerProtocol(Port):
    pass


class CommandHandler(HandlerProtocol, Generic[TCommand]):
    @abstractmethod
    def handle(self, command: Command[TEntity, TResult]) -> TResult: ...


class QueryHandler(HandlerProtocol, Generic[TQuery]):
    @abstractmethod
    def handle(self, query: Query[TEntity, TResult]) -> TResult: ...


class AsyncCommandHandler(HandlerProtocol, Generic[TCommand]):
    @abstractmethod
    async def handle(self, command: Command[TEntity, TResult]) -> TResult: ...


class AsyncQueryHandler(HandlerProtocol, Generic[TQuery]):
    @abstractmethod
    async def handle(self, query: Query[TEntity, TResult]) -> TResult: ...
