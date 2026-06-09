from __future__ import annotations

from typing import ClassVar

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.cache.null_cache import NullCache
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.event_bus.null_event_bus import NullEventBus
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.application.logger.null_logger import NullLogger
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.event_emitter import Event, EventEmitter
from aod._internal.core.fields.fields import Field, PrivateField


class BaseOperation(BaseBehaviour):
    __skip_method_wrapping__: ClassVar[bool] = True
    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)
    events: list[Event] = Field(default_factory=list, init=False)
    logger: Logger | AsyncLogger = Field(default_factory=NullLogger)
    event_bus: EventBus | AsyncEventBus = Field(default_factory=NullEventBus)
    cache: Cache | AsyncCache = Field(default_factory=NullCache)