from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

from aod._internal.application.cache.cache import BaseCache
from aod._internal.application.contracts import Command, Query
from aod._internal.core.async_utils import should_await
from aod._internal.core.base_operation import BaseOperation


class CacheContext:
    def __init__(self, caches: list[BaseCache] | None = None) -> None:
        self._caches = caches or []

    def get_for(self, key_material: Query | BaseOperation) -> BaseCache | None:
        for cache in self._caches:
            for key_obj in cache.keys:
                if isinstance(key_material, key_obj.get_type()):
                    return cache
        return None

    def get(self, key_material: Query | BaseOperation) -> Any:
        cache = self.get_for(key_material)
        if cache is None:
            return None
        return cache._get(key_material)

    async def get_async(self, key_material: Query | BaseOperation) -> Any:
        cache = self.get_for(key_material)
        if cache is None:
            return None
        return await should_await(cache._get(key_material))

    def set(self, key_material: Query | BaseOperation, value: Any) -> None:
        cache = self.get_for(key_material)
        if cache is None:
            return
        cache._set(key_material, value)

    def delete(self, command: Command | BaseOperation) -> None:
        for cache in self._caches:
            cache._delete(command)

    def flush(self) -> None:
        for cache in self._caches:
            cache._flush()

    async def flush_async(self) -> None:
        for cache in self._caches:
            await should_await(cache._flush())

    def discard(self) -> None:
        for cache in self._caches:
            cache._to_set.clear()
            cache._to_delete.clear()


_cache_context: ContextVar[CacheContext] = ContextVar("_cache_context")


class CacheManager:
    def __init__(self, *caches: BaseCache) -> None:
        self._caches = list(set(caches))
        self._token: Token[CacheContext] | None = None

    def __enter__(self) -> CacheManager:
        cache_context = CacheContext(self._caches)
        self._token = _cache_context.set(cache_context)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._token is None:
            return
        _cache_context.reset(self._token)


def get_cache_context() -> CacheContext:
    try:
        return _cache_context.get()
    except LookupError:
        return CacheContext()
