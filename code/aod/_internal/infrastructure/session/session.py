from __future__ import annotations

from abc import abstractmethod

from aod._internal.application.port import Port


class Session(Port):
    @abstractmethod
    def execute(self, operation: object) -> object: ...

    @abstractmethod
    def query(self, operation: object) -> object: ...

    @abstractmethod
    def begin(self) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class AsyncSession(Port):
    @abstractmethod
    async def execute(self, operation: object) -> object: ...

    @abstractmethod
    async def query(self, operation: object) -> object: ...

    @abstractmethod
    async def begin(self) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...
