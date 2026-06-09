from __future__ import annotations

from abc import abstractmethod
from typing import Any, Generic, TypeVar

from aod._internal.application.contracts import Command, Query
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.infrastructure.session import AsyncSession, Session

TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)


class BaseHandler(BaseSealed):
    session: Session | None = None


class AsyncBaseHandler(BaseHandler):
    session: AsyncSession | None = None


class CommandHandler(BaseHandler, Generic[TCommand]):
    @abstractmethod
    def handle(self, command: TCommand) -> Any: ...


class QueryHandler(BaseHandler, Generic[TQuery]):
    @abstractmethod
    def handle(self, query: TQuery) -> Any: ...


class AsyncCommandHandler(AsyncBaseHandler, Generic[TCommand]):
    @abstractmethod
    async def handle(self, command: TCommand) -> Any: ...


class AsyncQueryHandler(AsyncBaseHandler, Generic[TQuery]):
    @abstractmethod
    async def handle(self, query: TQuery) -> Any: ...
