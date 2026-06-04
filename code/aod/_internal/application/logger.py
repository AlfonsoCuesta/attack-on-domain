from __future__ import annotations

from abc import abstractmethod

from aod._internal.application.port import Port


class Logger(Port):
    @abstractmethod
    def debug(self, msg: str, **context: object) -> None: ...

    @abstractmethod
    def info(self, msg: str, **context: object) -> None: ...

    @abstractmethod
    def warning(self, msg: str, **context: object) -> None: ...

    @abstractmethod
    def error(self, msg: str, **context: object) -> None: ...
