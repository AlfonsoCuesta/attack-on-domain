from __future__ import annotations

from aod._internal.core.event_emitter import Event
from aod._internal.core.fields.fields import PrivateField
from aod.application.async_ import EventBus as AsyncEventBus, Logger as AsyncLogger, UnitOfWork as AsyncUnitOfWork
from aod.testing.doubles.application.logger import LogEntry


class AsyncSpyLogger(AsyncLogger):
    _entries: list[LogEntry] = PrivateField(default_factory=list)

    @property
    def entries(self) -> list[LogEntry]:
        return list(self._entries)

    async def debug(self, msg: str, **context: object) -> None:
        self._entries.append(LogEntry("debug", msg, **context))

    async def info(self, msg: str, **context: object) -> None:
        self._entries.append(LogEntry("info", msg, **context))

    async def warning(self, msg: str, **context: object) -> None:
        self._entries.append(LogEntry("warning", msg, **context))

    async def error(self, msg: str, **context: object) -> None:
        self._entries.append(LogEntry("error", msg, **context))


class AsyncSpyEventBus(AsyncEventBus):
    _published: list[Event] = PrivateField(default_factory=list)

    @property
    def published(self) -> list[Event]:
        return list(self._published)

    async def publish(self, *events: Event) -> None:
        self._published.extend(events)


class AsyncSpyUnitOfWork(AsyncUnitOfWork):
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

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        self._rolled_back = True

    async def flush(self) -> None:
        self._flushed = True
