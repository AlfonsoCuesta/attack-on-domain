from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from aod._internal.application.contracts import Command, Query

from .base_handler import AsyncBaseHandler, BaseHandler

TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)
TResult = TypeVar("TResult")


class CommandHandler(BaseHandler, Generic[TCommand]):
    @abstractmethod
    def handle(self, command: TCommand) -> TResult: ...


class QueryHandler(BaseHandler, Generic[TQuery]):
    @abstractmethod
    def handle(self, query: TQuery) -> TResult: ...


class AsyncCommandHandler(AsyncBaseHandler, Generic[TCommand]):
    @abstractmethod
    async def handle(self, command: TCommand) -> TResult: ...


class AsyncQueryHandler(AsyncBaseHandler, Generic[TQuery]):
    @abstractmethod
    async def handle(self, query: TQuery) -> TResult: ...
