from __future__ import annotations

from typing import Any

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.application.unit_of_work import AsyncUnitOfWork, UnitOfWork
from aod._internal.testing.doubles.stubs import port_stub

SpyLogger: Any = port_stub(Logger)
SpyEventBus: Any = port_stub(EventBus)
SpyUnitOfWork: Any = port_stub(UnitOfWork)
SpyCache: Any = port_stub(Cache)

AsyncSpyLogger: Any = port_stub(AsyncLogger)
AsyncSpyEventBus: Any = port_stub(AsyncEventBus)
AsyncSpyUnitOfWork: Any = port_stub(AsyncUnitOfWork)
AsyncSpyCache: Any = port_stub(AsyncCache)
