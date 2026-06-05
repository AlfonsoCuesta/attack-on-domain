from __future__ import annotations

from abc import abstractmethod
from typing import TypeVar, cast

from aod._internal.application.repository import Command, Query

from .unit_of_work import _UnitOfWorkBase

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")


class UnitOfWork(_UnitOfWorkBase):
    async def command(self, cmd: Command[TEntity, TResult]) -> TResult:
        result = cast(TResult, await self._resolve_repo(cmd).command(cmd))
        self.is_dirty = True
        return result

    async def query(self, query: Query[TEntity, TResult]) -> TResult:
        return cast(TResult, await self._resolve_repo(query).query(query))

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def flush(self) -> None: ...
