from __future__ import annotations

from typing import Generic, TypeVar

from aod._internal.core.base_sealed import BaseSealed

T = TypeVar("T")


class ProjectionQuery(BaseSealed, Generic[T]):
    pass


class ProjectionCommand(BaseSealed, Generic[T]):
    pass
