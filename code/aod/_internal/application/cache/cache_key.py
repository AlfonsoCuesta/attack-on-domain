from __future__ import annotations

from abc import abstractmethod
from typing import Any, Callable, ClassVar, TypeVar

from aod._internal.application.contracts import Query
from aod._internal.core.base_guarded import BaseGuarded
from aod._internal.core.base_sealed import BaseSealed

TQuery_co = TypeVar("TQuery_co", bound=Query, covariant=True)
TOperation = TypeVar("TOperation")


class CacheInvalidation(BaseSealed):
    target_type: type
    key_fn: Callable[..., str]


class CacheKey(BaseGuarded):
    __skip_method_wrapping__: ClassVar[bool] = True
    ttl: float | None = None

    @abstractmethod
    def key(self, *args: Any, **kwargs: Any) -> str: ...

    @abstractmethod
    def invalidate(self) -> list[CacheInvalidation]: ...

    @classmethod
    @abstractmethod
    def get_type(cls) -> type: ...

    def get_invalidation_key_fn(self, invalidation_type: type) -> Callable[..., str] | None:
        for inv in self.invalidate():
            if inv.target_type is invalidation_type:
                return inv.key_fn
        return None
