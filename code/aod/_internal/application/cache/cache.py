from __future__ import annotations

from abc import abstractmethod
from typing import Any

from aod._internal.application.port import Port


class Cache(Port):
    @abstractmethod
    def get(self, key: str) -> Any: ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: float | None = None) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...
