from __future__ import annotations

from typing import Any

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.testing.doubles.spies import spy_port

SpyLogger: Any = spy_port(Logger)
SpyEventBus: Any = spy_port(EventBus)
SpyCache: Any = spy_port(Cache)

AsyncSpyLogger: Any = spy_port(AsyncLogger)
AsyncSpyEventBus: Any = spy_port(AsyncEventBus)
AsyncSpyCache: Any = spy_port(AsyncCache)
