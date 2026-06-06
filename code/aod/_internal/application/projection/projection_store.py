from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from aod._internal.application.projection.projection import Projection

T = TypeVar("T")


@runtime_checkable
class ProjectionStore(Protocol):
    def projection(self, projection: Projection[T]) -> T: ...
