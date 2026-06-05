from __future__ import annotations

from aod.application import Logger
from aod._internal.core.fields.fields import PrivateField


class LogEntry:
    def __init__(self, level: str, msg: str, **context: object) -> None:
        self.level = level
        self.msg = msg
        self.context = context


class SpyLogger(Logger):
    _entries: list[LogEntry] = PrivateField(default_factory=list)

    @property
    def entries(self) -> list[LogEntry]:
        return list(self._entries)

    def debug(self, msg: str, **context: object) -> None:
        self._entries.append(LogEntry("debug", msg, **context))

    def info(self, msg: str, **context: object) -> None:
        self._entries.append(LogEntry("info", msg, **context))

    def warning(self, msg: str, **context: object) -> None:
        self._entries.append(LogEntry("warning", msg, **context))

    def error(self, msg: str, **context: object) -> None:
        self._entries.append(LogEntry("error", msg, **context))
