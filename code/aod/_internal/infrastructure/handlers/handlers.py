from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler import (
    AsyncCommandHandler as AppAsyncCommandHandler,
)
from aod._internal.application.handler import (
    AsyncQueryHandler as AppAsyncQueryHandler,
)
from aod._internal.application.handler import (
    CommandHandler as AppCommandHandler,
)
from aod._internal.application.handler import (
    QueryHandler as AppQueryHandler,
)
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.infrastructure.session import AsyncSession, Session

TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)


class BaseHandler(BaseBehaviour):
    session: Session | None = None


class AsyncBaseHandler(BaseHandler):
    session: AsyncSession | None = None


class CommandHandler(BaseHandler, AppCommandHandler, Generic[TCommand]):
    @abstractmethod
    def handle(self, command: TCommand) -> object: ...


class QueryHandler(BaseHandler, AppQueryHandler, Generic[TQuery]):
    @abstractmethod
    def handle(self, query: TQuery) -> object: ...


class AsyncCommandHandler(AsyncBaseHandler, AppAsyncCommandHandler, Generic[TCommand]):
    @abstractmethod
    async def handle(self, command: TCommand) -> object: ...


class AsyncQueryHandler(AsyncBaseHandler, AppAsyncQueryHandler, Generic[TQuery]):
    @abstractmethod
    async def handle(self, query: TQuery) -> object: ...
