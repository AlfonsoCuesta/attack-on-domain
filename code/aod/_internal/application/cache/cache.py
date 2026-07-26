from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Any

from aod._internal.application.cache.cache_key import CacheKey
from aod._internal.application.contracts import Command, Query
from aod._internal.application.port import Port
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.fields.fields import Field, PrivateField


@dataclass
class _CacheEntry:
    key: str
    value: Any
    ttl: float | None = None


class BaseCache(Port):
    keys: list[CacheKey] = Field(default_factory=list)
    _to_set: list[_CacheEntry] = PrivateField(default_factory=list)
    _to_delete: list[str] = PrivateField(default_factory=list)

    def _set(self, key_material: Query | BaseOperation, value: Any) -> None:
        key = self._resolve_key(key_material)
        ttl = self._resolve_ttl(key_material)
        self._to_set.append(_CacheEntry(key, value, ttl))

    def _delete(self, command: Command | BaseOperation) -> None:
        for key_obj in self.keys:
            fn = key_obj.get_invalidation_key_fn(type(command))
            if fn is not None:
                self._to_delete.append(fn(command))

    def _resolve_key(self, key_material: Query | BaseOperation) -> str:
        for key_obj in self.keys:
            if isinstance(key_material, key_obj.get_type()):
                return key_obj.key(key_material)
        raise RuntimeError(f"No cache key registered for {type(key_material).__name__}")

    def _resolve_ttl(self, key_material: Query | BaseOperation) -> float | None:
        for key_obj in self.keys:
            if isinstance(key_material, key_obj.get_type()):
                return key_obj.ttl
        return None


class Cache(BaseCache):
    def _get(self, key_material: Query | BaseOperation) -> Any:
        key = self._resolve_key(key_material)
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
    def get(self, key: str) -> Any:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError()  # pragma: no cover


class AsyncCache(BaseCache):
    async def _get(self, key_material: Query | BaseOperation) -> Any:
        key = self._resolve_key(key_material)
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
    async def get(self, key: str) -> Any:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    async def delete(self, key: str) -> None:
        raise NotImplementedError()  # pragma: no cover
