from __future__ import annotations

from typing import Any

from aod._internal.core.fields.fields import PrivateField
from aod._internal.infrastructure.cache.cache import AsyncCache as InfraAsyncCache
from aod._internal.infrastructure.cache.cache import Cache as InfraCache


class SpyCache(InfraCache):
    _get_calls: list[str] = PrivateField(default_factory=list)
    _set_calls: list[tuple[str, Any, float | None]] = PrivateField(default_factory=list)
    _delete_calls: list[str] = PrivateField(default_factory=list)
    _flush_calls: list[None] = PrivateField(default_factory=list)
    _set_promise_calls: list[tuple[str, Any, float | None]] = PrivateField(default_factory=list)
    _delete_promise_calls: list[str] = PrivateField(default_factory=list)
    _data: dict[str, Any] = PrivateField(default_factory=dict)

    @property
    def get_calls(self) -> list[str]:
        return list(self._get_calls)

    @property
    def set_calls(self) -> list[tuple[str, Any, float | None]]:
        return list(self._set_calls)

    @property
    def delete_calls(self) -> list[str]:
        return list(self._delete_calls)

    @property
    def flush_calls(self) -> list[None]:
        return list(self._flush_calls)

    @property
    def set_promise_calls(self) -> list[tuple[str, Any, float | None]]:
        return list(self._set_promise_calls)

    @property
    def delete_promise_calls(self) -> list[str]:
        return list(self._delete_promise_calls)

    def get(self, key: str) -> Any:
        self._get_calls.append(key)
        return self._data.get(key)

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        self._set_calls.append((key, value, ttl))
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._delete_calls.append(key)
        self._data.pop(key, None)

    def set_promise(self, key: str, value: Any, ttl: float | None = None) -> None:
        self._set_promise_calls.append((key, value, ttl))
        super().set_promise(key, value, ttl)

    def delete_promise(self, key: str) -> None:
        self._delete_promise_calls.append(key)
        super().delete_promise(key)

    def flush(self) -> None:
        self._flush_calls.append(None)
        super().flush()


class AsyncSpyCache(InfraAsyncCache):
    _get_calls: list[str] = PrivateField(default_factory=list)
    _set_calls: list[tuple[str, Any, float | None]] = PrivateField(default_factory=list)
    _delete_calls: list[str] = PrivateField(default_factory=list)
    _flush_calls: list[None] = PrivateField(default_factory=list)
    _set_promise_calls: list[tuple[str, Any, float | None]] = PrivateField(default_factory=list)
    _delete_promise_calls: list[str] = PrivateField(default_factory=list)
    _data: dict[str, Any] = PrivateField(default_factory=dict)

    @property
    def get_calls(self) -> list[str]:
        return list(self._get_calls)

    @property
    def set_calls(self) -> list[tuple[str, Any, float | None]]:
        return list(self._set_calls)

    @property
    def delete_calls(self) -> list[str]:
        return list(self._delete_calls)

    @property
    def flush_calls(self) -> list[None]:
        return list(self._flush_calls)

    @property
    def set_promise_calls(self) -> list[tuple[str, Any, float | None]]:
        return list(self._set_promise_calls)

    @property
    def delete_promise_calls(self) -> list[str]:
        return list(self._delete_promise_calls)

    async def get(self, key: str) -> Any:
        self._get_calls.append(key)
        return self._data.get(key)

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        self._set_calls.append((key, value, ttl))
        self._data[key] = value

    async def delete(self, key: str) -> None:
        self._delete_calls.append(key)
        self._data.pop(key, None)

    def set_promise(self, key: str, value: Any, ttl: float | None = None) -> None:
        self._set_promise_calls.append((key, value, ttl))
        super().set_promise(key, value, ttl)

    def delete_promise(self, key: str) -> None:
        self._delete_promise_calls.append(key)
        super().delete_promise(key)

    async def flush(self) -> None:
        self._flush_calls.append(None)
        await super().flush()
