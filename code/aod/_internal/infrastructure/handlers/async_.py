from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from aod._internal.application.repository import Command, Query

from .base_handler import AsyncBaseHandler

C = TypeVar("C", bound=Command)
Q = TypeVar("Q", bound=Query)


class CommandHandler(AsyncBaseHandler, Generic[C]):
    @abstractmethod
    async def handle(self, cmd: C) -> object: ...


class QueryHandler(AsyncBaseHandler, Generic[Q]):
    @abstractmethod
    async def handle(self, query: Q) -> object: ...
