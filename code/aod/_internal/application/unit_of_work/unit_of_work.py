from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class UnitOfWork(Protocol):
    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def flush(self) -> None: ...


@runtime_checkable
class AsyncUnitOfWork(Protocol):
    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def flush(self) -> None: ...