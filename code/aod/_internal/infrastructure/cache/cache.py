from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Any

from aod._internal.core.fields.fields import PrivateField
from aod.application import Port


@dataclass
class _SetItem:
    key: str
    value: Any
    ttl: float | None = None


class Cache(Port):
    _delete_items: list[str] = PrivateField(default_factory=list)
    _set_items: list[_SetItem] = PrivateField(default_factory=list)

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

    @abstractmethod
    def get(self, key: str) -> Any: ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: float | None = None) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class AsyncCache(Port):
    _delete_items: list[str] = PrivateField(default_factory=list)
    _set_items: list[_SetItem] = PrivateField(default_factory=list)

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

    @abstractmethod
    async def get(self, key: str) -> Any: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: float | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...
