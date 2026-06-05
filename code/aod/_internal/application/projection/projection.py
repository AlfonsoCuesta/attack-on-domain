from __future__ import annotations

from typing import Generic, TypeVar

from aod._internal.core.base_sealed import BaseSealed

T = TypeVar("T")


class Projection(BaseSealed, Generic[T]):
    pass
