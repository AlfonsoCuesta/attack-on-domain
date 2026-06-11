from __future__ import annotations

from aod._internal.application.unit_of_work.unit_of_work import AsyncUnitOfWork, UnitOfWork
from aod._internal.core.fields.fields import PrivateField


class SpyUnitOfWork(UnitOfWork):
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)
    _flushed: bool = PrivateField(default=False)

    @property
    def committed(self) -> bool:
        return self._committed

    @property
    def rolled_back(self) -> bool:
        return self._rolled_back

    @property
    def flushed(self) -> bool:
        return self._flushed

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        self._rolled_back = True

    def begin(self) -> None: ...

    def flush(self) -> None:
        self._flushed = True


class AsyncSpyUnitOfWork(AsyncUnitOfWork):
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)
    _flushed: bool = PrivateField(default=False)

    @property
    def committed(self) -> bool:
        return self._committed

    @property
    def rolled_back(self) -> bool:
        return self._rolled_back

    @property
    def flushed(self) -> bool:
        return self._flushed

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        self._rolled_back = True

    async def begin(self) -> None: ...

    async def flush(self) -> None:
        self._flushed = True
