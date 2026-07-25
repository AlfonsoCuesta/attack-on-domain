from __future__ import annotations

from typing import Any

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.testing.doubles.stubs import port_stub

SpyLogger: Any = port_stub(Logger)
SpyEventBus: Any = port_stub(EventBus)
SpyCache: Any = port_stub(Cache)

AsyncSpyLogger: Any = port_stub(AsyncLogger)
AsyncSpyEventBus: Any = port_stub(AsyncEventBus)
AsyncSpyCache: Any = port_stub(AsyncCache)
