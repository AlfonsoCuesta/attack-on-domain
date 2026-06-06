from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from aod._internal.application.projection.projection import ProjectionCommand, ProjectionQuery

T = TypeVar("T")


@runtime_checkable
class ProjectionStore(Protocol):
    async def query(self, query: ProjectionQuery[T]) -> T: ...
    async def command(self, command: ProjectionCommand[T]) -> T: ...
