from __future__ import annotations

from abc import abstractmethod
from typing import Any, TypeVar, cast

from aod._internal.application.projection.projection import Projection
from aod._internal.application.projection.projection_store import ProjectionStore
from aod._internal.application.projection.async_ import ProjectionStore as AsyncProjectionStore
from aod._internal.application.repository import Command, Query, Repository
from aod._internal.application.repository.async_ import Repository as AsyncRepository
from aod._internal.core.async_utils import should_await
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.domain.entity import RootEntity

from .unit_of_work import _NullProjectionStore, _UnitOfWorkBase

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")
T = TypeVar("T")


class UnitOfWork(_UnitOfWorkBase):
    repositories: list[Repository[Any, Any] | AsyncRepository[Any, Any]] = Field(default_factory=list)
    projection_store: ProjectionStore | AsyncProjectionStore = Field(default_factory=_NullProjectionStore)
    is_dirty: bool = Field(default=False, init=False)
    _repo_map: dict[type[RootEntity], Repository[Any, Any] | AsyncRepository[Any, Any]] = PrivateField(default_factory=dict)

    async def command(self, cmd: Command[TEntity, TResult]) -> TResult:
        result = await should_await(self._resolve_repo(cmd).command(cmd))
        self.is_dirty = True
        return cast(TResult, result)

    async def query(self, query: Query[TEntity, TResult]) -> TResult:
        return cast(TResult, await should_await(self._resolve_repo(query).query(query)))

    async def projection(self, p: Projection[T]) -> T:
        return cast(T, await should_await(self.projection_store.projection(p)))

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def flush(self) -> None: ...
