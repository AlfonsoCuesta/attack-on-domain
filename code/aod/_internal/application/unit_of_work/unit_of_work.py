from __future__ import annotations

from abc import abstractmethod
from typing import Any

from aod._internal.application.port import Port
from aod._internal.core.event_emitter import Event


class UnitOfWork(Port):
    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def begin(self) -> None: ...

    @abstractmethod
    def add_handler(self, handler: Any) -> None: ...


class AsyncUnitOfWork(Port):
    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def begin(self) -> None: ...

    @abstractmethod
    def add_handler(self, handler: Any) -> None: ...
