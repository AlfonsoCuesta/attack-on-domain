from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar, cast

from aod._internal.application.projection.projection import Projection
from aod._internal.core.async_utils import should_await
from aod._internal.core.fields.fields import Field, PrivateField

from .projection_handler import ProjectionHandler as SyncProjectionHandler
from .projection_store import ProjectionStore as SyncProjectionStore

P = TypeVar("P", bound=Projection)
T = TypeVar("T")


class ProjectionHandler(SyncProjectionHandler, Generic[P]):
    @abstractmethod
    async def handle(self, projection: P) -> object: ...


class ProjectionStore(SyncProjectionStore):
    handlers: list[ProjectionHandler | SyncProjectionHandler] = Field(default_factory=list)
    _handlers: dict[type, ProjectionHandler | SyncProjectionHandler] = PrivateField(
        default_factory=dict
    )

    async def projection(self, p: Projection[T]) -> T:
        handler = self._get_handler(p)
        return cast(T, await should_await(handler.handle(p)))
