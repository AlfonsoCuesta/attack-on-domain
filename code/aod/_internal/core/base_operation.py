from __future__ import annotations

from typing import Any, ClassVar, get_origin, get_type_hints

from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.application.port import Port
from aod._internal.core.application_exception import InvalidUseCasePortFieldError
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.event_emitter import Event, EventEmitter
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.infrastructure.handlers.handlers import AsyncBaseHandler, BaseHandler


_SPECIAL_PORT_TYPES = (
    Logger,
    AsyncLogger,
    EventBus,
    AsyncEventBus,
)


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
    _loggers: list[Logger | AsyncLogger] = PrivateField(default_factory=list)
    _event_buses: list[EventBus | AsyncEventBus] = PrivateField(default_factory=list)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._collect_special_ports()

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

    def _collect_special_ports(self) -> None:
        loggers: list[Logger | AsyncLogger] = []
        event_buses: list[EventBus | AsyncEventBus] = []

        for field_name in self.__model_fields__:
            value = object.__getattribute__(self, field_name)
            if isinstance(value, (Logger, AsyncLogger)):
                loggers.append(value)
            elif isinstance(value, (EventBus, AsyncEventBus)):
                event_buses.append(value)

        object.__setattr__(self, "_loggers", loggers)
        object.__setattr__(self, "_event_buses", event_buses)
