from __future__ import annotations

from typing import Any, ClassVar, get_origin, get_type_hints

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.cache.null_cache import NullCache
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.event_bus.null_event_bus import NullEventBus
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.application.logger.null_logger import NullLogger
from aod._internal.application.port import Port
from aod._internal.core.application_exception import InvalidUseCasePortFieldError
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.event_emitter import Event, EventEmitter
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.infrastructure.handlers.handlers import AsyncBaseHandler, BaseHandler


def _resolve_port_class(tp: Any) -> type | None:
    if isinstance(tp, type):
        return tp
    origin = get_origin(tp)
    if isinstance(origin, type):
        return origin
    return None


class BaseOperation(BaseBehaviour):
    __skip_method_wrapping__: ClassVar[bool] = True
    __skip_port_check__: ClassVar[bool] = True
    __not_allowed_port_types__ = ()
    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)
    events: list[Event] = Field(default_factory=list, init=False)
    logger: Logger | AsyncLogger = Field(default_factory=NullLogger)
    event_bus: EventBus | AsyncEventBus = Field(default_factory=NullEventBus)
    cache: Cache | AsyncCache = Field(default_factory=NullCache)

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__dict__.get("__skip_port_check__"):
            return
        try:
            hints = get_type_hints(cls)
        except Exception:
            hints = {}
        own_annotations = getattr(cls, "__annotations__", {})
        for field_name in own_annotations:
            if field_name.startswith("_"):
                continue
            tp = hints.get(field_name)
            if tp is None:
                continue
            resolved = _resolve_port_class(tp)
            if resolved is None or not issubclass(resolved, Port):
                raise InvalidUseCasePortFieldError(
                    field_name,
                    cls.__name__,
                    str(tp),
                )
            if issubclass(
                resolved, (BaseHandler, AsyncBaseHandler, *cls.__not_allowed_port_types__)
            ):
                raise InvalidUseCasePortFieldError(
                    field_name,
                    cls.__name__,
                    str(tp),
                )
