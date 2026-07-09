from __future__ import annotations

from abc import abstractmethod
from typing import Any

from aod._internal.application.port import Port


class Cache(Port):
    @abstractmethod
    def flush(self) -> None: ...

    @abstractmethod
    def get(self, key: str) -> Any: ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: float | None = None) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def delete_promise(self, key: str) -> None: ...

    @abstractmethod
    def set_promise(self, key: str, value: Any, ttl: float | None = None) -> None: ...

    def get_cache_key(self, query: object) -> str:
        raise NotImplementedError(
            "get_cache_key is not implemented for this cache. "
            "Use aod.infrastructure.Cache with CacheKey instances."
        )

    def get_invalidate_key(self, command: object) -> str | None:
        return None


class AsyncCache(Port):
    @abstractmethod
    async def flush(self) -> None: ...

    @abstractmethod
    async def get(self, key: str) -> Any: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: float | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    def delete_promise(self, key: str) -> None: ...

    @abstractmethod
    def set_promise(self, key: str, value: Any, ttl: float | None = None) -> None: ...

    def get_cache_key(self, query: object) -> str:
        raise NotImplementedError(
            "get_cache_key is not implemented for this cache. "
            "Use aod.infrastructure.Cache with CacheKey instances."
        )

    def get_invalidate_key(self, command: object) -> str | None:
        return None
