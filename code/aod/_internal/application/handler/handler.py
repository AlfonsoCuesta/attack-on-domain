from abc import abstractmethod
from typing import Generic, TypeVar

from aod._internal.application.contracts import Command, Query
from aod._internal.application.port import Port

TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)


class HandlerProtocol(Port):
    pass


class CommandHandler(HandlerProtocol, Generic[TCommand]):
    @abstractmethod
    def handle(self, command: TCommand) -> object: ...


class QueryHandler(HandlerProtocol, Generic[TQuery]):
    @abstractmethod
    def handle(self, query: TQuery) -> object: ...


class AsyncCommandHandler(HandlerProtocol, Generic[TCommand]):
    @abstractmethod
    async def handle(self, command: TCommand) -> object: ...


class AsyncQueryHandler(HandlerProtocol, Generic[TQuery]):
    @abstractmethod
    async def handle(self, query: TQuery) -> object: ...
