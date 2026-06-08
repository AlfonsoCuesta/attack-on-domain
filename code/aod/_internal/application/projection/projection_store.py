from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from aod._internal.application.projection.projection import (
    ProjectionCommand,
    ProjectionQuery,
    ReadModel,
)

T = TypeVar("T", bound=ReadModel | None)


@runtime_checkable
class ProjectionStore(Protocol):
    def query(self, query: ProjectionQuery[T]) -> T: ...
    def command(self, command: ProjectionCommand[T]) -> T: ...


@runtime_checkable
class AsyncProjectionStore(Protocol):
    async def query(self, query: ProjectionQuery[T]) -> T: ...
    async def command(self, command: ProjectionCommand[T]) -> T: ...
