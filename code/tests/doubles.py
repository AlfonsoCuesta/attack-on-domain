from __future__ import annotations

from typing import Any

from aod.application import EventBus, Logger, UnitOfWork
from aod._internal.core.event_emitter import Event


class LogEntry:
    def __init__(self, level: str, msg: str, **context: object) -> None:
        self.level = level
        self.msg = msg
        self.context = context


class SpyLogger(Logger):
    def __init__(self, **data: object) -> None:
        object.__setattr__(self, "_entries", [])
        super().__init__(**data)

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


class SpyEventBus(EventBus):
    def __init__(self, **data: object) -> None:
        object.__setattr__(self, "_published", [])
        super().__init__(**data)

    @property
    def published(self) -> list[Event]:
        return list(self._published)

    def publish(self, *events: Event) -> None:
        self._published.extend(events)


class SpyUnitOfWork(UnitOfWork):
    def __init__(self, **data: Any) -> None:
        dirty = data.pop("dirty", False)
        object.__setattr__(self, "_committed", False)
        object.__setattr__(self, "_rolled_back", False)
        object.__setattr__(self, "_flushed", False)
        super().__init__(**data)
        if dirty:
            object.__setattr__(self, "is_dirty", True)

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
