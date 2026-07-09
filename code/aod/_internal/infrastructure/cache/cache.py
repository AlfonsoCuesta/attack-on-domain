from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Any

from aod._internal.application.cache.cache import AsyncCache as AppAsyncCache
from aod._internal.application.cache.cache import Cache as AppCache
from aod._internal.application.cache.cache_key import CacheKey
from aod._internal.core.fields.fields import PrivateField


@dataclass
class _SetItem:
    key: str
    value: Any
    ttl: float | None = None


class Cache(AppCache):
    _keys: list[CacheKey] = PrivateField(default_factory=list)
    _delete_items: list[str] = PrivateField(default_factory=list)
    _set_items: list[_SetItem] = PrivateField(default_factory=list)

    def __init__(self, *, keys: list[CacheKey] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if keys is not None:
            object.__setattr__(self, "_keys", list(keys))

    def set_promise(self, key: str, value: Any, ttl: float | None = None) -> None:
        self._set_items.append(_SetItem(key, value, ttl))

    def delete_promise(self, key: str) -> None:
        self._delete_items.append(key)

    def flush(self) -> None:
        if self._delete_items:
            for key in self._delete_items:
                self.delete(key)
        if self._set_items:
            for item in self._set_items:
                self.set(item.key, item.value, item.ttl)
        self._delete_items.clear()
        self._set_items.clear()

    def get_cache_key(self, query: object) -> str:
        for key_obj in self._keys:
            query_type = key_obj.get_query_type()
            if isinstance(query, query_type):
                return key_obj.key(query)
        raise RuntimeError(f"No cache key registered for {type(query).__name__}")

    def get_invalidate_key(self, command: object) -> str | None:
        for key_obj in self._keys:
            fn = key_obj.get_invalidation_key_fn(type(command))
            if fn is not None:
                return fn(command)
        return None

    @abstractmethod
    def get(self, key: str) -> Any: ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: float | None = None) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class AsyncCache(AppAsyncCache):
    _keys: list[CacheKey] = PrivateField(default_factory=list)
    _delete_items: list[str] = PrivateField(default_factory=list)
    _set_items: list[_SetItem] = PrivateField(default_factory=list)

    def __init__(self, *, keys: list[CacheKey] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if keys is not None:
            object.__setattr__(self, "_keys", list(keys))

    def set_promise(self, key: str, value: Any, ttl: float | None = None) -> None:
        self._set_items.append(_SetItem(key, value, ttl))

    def delete_promise(self, key: str) -> None:
        self._delete_items.append(key)

    async def flush(self) -> None:
        if self._delete_items:
            for key in self._delete_items:
                await self.delete(key)
        if self._set_items:
            for item in self._set_items:
                await self.set(item.key, item.value, item.ttl)
        self._delete_items.clear()
        self._set_items.clear()

    def get_cache_key(self, query: object) -> str:
        for key_obj in self._keys:
            query_type = key_obj.get_query_type()
            if isinstance(query, query_type):
                return key_obj.key(query)
        raise RuntimeError(f"No cache key registered for {type(query).__name__}")

    def get_invalidate_key(self, command: object) -> str | None:
        for key_obj in self._keys:
            fn = key_obj.get_invalidation_key_fn(type(command))
            if fn is not None:
                return fn(command)
        return None

    @abstractmethod
    async def get(self, key: str) -> Any: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: float | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...
