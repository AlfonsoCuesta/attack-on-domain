from __future__ import annotations

from typing import ClassVar, cast

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.cache.null_cache import NullCache
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.event_bus.null_event_bus import NullEventBus
from aod._internal.application.handler.handler import HandlerProtocol
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.application.logger.null_logger import NullLogger
from aod._internal.application.port import Port
from aod._internal.core.application_exception import InvalidPortFieldError
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.base_validator import BaseValidator
from aod._internal.core.event_emitter import Event, EventEmitter
from aod._internal.core.fields.fields import Field, PrivateField


class BaseOperation(BaseBehaviour):
    __skip_method_wrapping__: ClassVar[bool] = True
    __skip_port_check__: ClassVar[bool] = True
    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)
    events: list[Event] = Field(default_factory=list, init=False)
    logger: Logger | AsyncLogger = Field(default_factory=NullLogger)
    event_bus: EventBus | AsyncEventBus = Field(default_factory=NullEventBus)
    cache: Cache | AsyncCache = Field(default_factory=NullCache)

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        for subcls in cls.__mro__:
            if "__skip_port_check__" in subcls.__dict__:
                return
            subcls = cast(BaseValidator, subcls)
            for field_name, field_info in subcls.__model_fields__.items():
                if field_name.startswith("_"):
                    continue
                if field_name not in cls.__annotations__:
                    continue

                tp = field_info.annotation
                if (
                    isinstance(tp, type)
                    and issubclass(tp, Port)
                    and not issubclass(tp, HandlerProtocol)
                ):
                    continue

                raise InvalidPortFieldError(
                    field_name,
                    cls.__name__,
                    str(field_info.annotation),
                )
