from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from aod._internal.application.repository import Command, Query

from .handlers import CommandHandler as SyncCommandHandler
from .handlers import QueryHandler as SyncQueryHandler

C = TypeVar("C", bound=Command)
Q = TypeVar("Q", bound=Query)


class CommandHandler(SyncCommandHandler, Generic[C]):
    @abstractmethod
    async def handle(self, cmd: C) -> object: ...


class QueryHandler(SyncQueryHandler, Generic[Q]):
    @abstractmethod
    async def handle(self, query: Q) -> object: ...
