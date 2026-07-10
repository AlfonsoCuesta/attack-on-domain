from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, TypeVar

from aod._internal.application.cache.cache_key import CacheKey
from aod._internal.application.contracts import Command, Query
from aod._internal.application.port import Port
from aod._internal.core.fields.fields import Field, PrivateField

TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)


@dataclass
class _CacheEntry:
    key: str
    value: Any
    ttl: float | None = None


class BaseCache(Port):
    keys: list[CacheKey] = Field(default_factory=list)
    _to_set: list[_CacheEntry] = PrivateField(default_factory=list)
    _to_delete: list[str] = PrivateField(default_factory=list)

    def _set(self, query: TQuery, value: Any) -> None:
        key = self._resolve_key(query)
        ttl = self._resolve_ttl(query)
        self._to_set.append(_CacheEntry(key, value, ttl))

    def _delete(self, command: TCommand) -> None:
        for key_obj in self.keys:
            fn = key_obj.get_invalidation_key_fn(type(command))
            if fn is not None:
                self._to_delete.append(fn(command))

    def _resolve_key(self, query: object) -> str:
        for key_obj in self.keys:
            query_type = key_obj.get_query_type()
            if isinstance(query, query_type):
                return key_obj.key(query)
        raise RuntimeError(f"No cache key registered for {type(query).__name__}")

    def _resolve_ttl(self, query: object) -> float | None:
        for key_obj in self.keys:
            if isinstance(query, key_obj.get_query_type()):
                return key_obj.ttl
        return None


class Cache(BaseCache):
    def _get(self, query: TQuery) -> Any:
        key = self._resolve_key(query)
        return self.get(key)

    def _flush(self) -> None:
        if self._to_delete:
            for key in self._to_delete:
                self.delete(key)
        if self._to_set:
            for entry in self._to_set:
                self.set(entry.key, entry.value, entry.ttl)
        self._to_delete.clear()
        self._to_set.clear()

    @abstractmethod
    def get(self, key: str) -> Any: ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: float | None = None) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class AsyncCache(BaseCache):
    async def _get(self, query: TQuery) -> Any:
        key = self._resolve_key(query)
        return await self.get(key)

    async def _flush(self) -> None:
        if self._to_delete:
            for key in self._to_delete:
                await self.delete(key)
        if self._to_set:
            for entry in self._to_set:
                await self.set(entry.key, entry.value, entry.ttl)
        self._to_delete.clear()
        self._to_set.clear()

    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: float | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...
