from __future__ import annotations

from abc import abstractmethod
from typing import TypeVar, cast

from aod._internal.application.projection import ProjectionCommand, ProjectionQuery, ReadModel
from aod._internal.application.projection.async_ import ProjectionStore as AsyncProjectionStore
from aod._internal.application.projection.projection_store import ProjectionStore
from aod._internal.application.repository import Command, Query, Repository
from aod._internal.application.repository.async_ import Repository as AsyncRepository
from aod._internal.core.async_utils import should_await
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.domain.entity import RootEntity

from .unit_of_work import _NullProjectionStore, _UnitOfWorkBase

T = TypeVar("T", bound=ReadModel | None)
TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")


class UnitOfWork(_UnitOfWorkBase):
    repositories: list[Repository | AsyncRepository] = Field(default_factory=list)
    projection_store: ProjectionStore | AsyncProjectionStore = Field(
        default_factory=_NullProjectionStore
    )
    is_dirty: bool = Field(default=False, init=False)
    _repo_map: dict[type[RootEntity], Repository | AsyncRepository] = PrivateField(
        default_factory=dict
    )

    async def command(self, command: Command | ProjectionCommand[T]) -> object:
        if isinstance(command, ProjectionCommand):
            return cast(object, await should_await(self.projection_store.command(command)))
        result = await should_await(self._resolve_repo(command).command(command))
        self.is_dirty = True
        return result

    async def query(self, query: Query | ProjectionQuery) -> object:
        if isinstance(query, ProjectionQuery):
            return cast(object, await should_await(self.projection_store.query(query)))
        return cast(object, await should_await(self._resolve_repo(query).query(query)))

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def flush(self) -> None: ...
