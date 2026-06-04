from __future__ import annotations

from abc import abstractmethod

from aod._internal.application.port import Port


class UnitOfWork(Port):
    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...
