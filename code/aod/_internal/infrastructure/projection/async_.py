from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from aod._internal.application.projection import Projection

from .projection import ProjectionHandler as SyncProjectionHandler

P = TypeVar("P", bound=Projection)


class ProjectionHandler(SyncProjectionHandler, Generic[P]):
    @abstractmethod
    async def handle(self, projection: P) -> object: ...
