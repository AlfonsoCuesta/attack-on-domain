from __future__ import annotations

from aod.application import UnitOfWork
from aod._internal.core.fields.fields import PrivateField


class SpyUnitOfWork(UnitOfWork):
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)
    _flushed: bool = PrivateField(default=False)

    def set_dirty(self) -> None:
        self.is_dirty = True

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

    def flush(self) -> None:
        self._flushed = True
