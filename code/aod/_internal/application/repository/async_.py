from __future__ import annotations

from typing import Generic, Protocol, TypeVar, runtime_checkable

from aod._internal.application.repository import Command, Query

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")


@runtime_checkable
class Repository(Protocol, Generic[TEntity, TResult]):
    async def command(self, cmd: Command[TEntity, TResult]) -> TResult: ...
    async def query(self, query: Query[TEntity, TResult]) -> TResult: ...
