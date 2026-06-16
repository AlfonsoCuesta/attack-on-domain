from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler import (
    AsyncCommandPort,
    AsyncQueryPort,
    CommandPort,
    QueryPort,
)
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.infrastructure.session import AsyncSession, Session

TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)


class BaseHandler(BaseBehaviour):
    session: Session | None = None


class AsyncBaseHandler(BaseHandler):
    session: AsyncSession | None = None


class CommandHandler(BaseHandler, CommandPort, Generic[TCommand]):
    @abstractmethod
    def handle(self, command: TCommand) -> object: ...  # ty:ignore[invalid-method-override]


class QueryHandler(BaseHandler, QueryPort, Generic[TQuery]):
    @abstractmethod
    def handle(self, query: TQuery) -> object: ...  # ty:ignore[invalid-method-override]


class AsyncCommandHandler(AsyncBaseHandler, AsyncCommandPort, Generic[TCommand]):
    @abstractmethod
    async def handle(self, command: TCommand) -> object: ...  # ty:ignore[invalid-method-override]


class AsyncQueryHandler(AsyncBaseHandler, AsyncQueryPort, Generic[TQuery]):
    @abstractmethod
    async def handle(self, query: TQuery) -> object: ...  # ty:ignore[invalid-method-override]
