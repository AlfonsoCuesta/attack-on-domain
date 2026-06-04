from __future__ import annotations

from abc import abstractmethod

from aod._internal.application.port import Port


class Logger(Port):
    @abstractmethod
    async def debug(self, msg: str, **context: object) -> None: ...
    @abstractmethod
    async def info(self, msg: str, **context: object) -> None: ...
    @abstractmethod
    async def warning(self, msg: str, **context: object) -> None: ...
    @abstractmethod
    async def error(self, msg: str, **context: object) -> None: ...
