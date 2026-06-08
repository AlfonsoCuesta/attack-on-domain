from __future__ import annotations

from abc import abstractmethod
from typing import Any

from aod._internal.application.port import Port


class Cache(Port):
    @abstractmethod
    async def get(self, key: str) -> Any: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: float | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...
