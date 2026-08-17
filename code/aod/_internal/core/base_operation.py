from __future__ import annotations

from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Callable, ClassVar, get_args, get_origin, get_type_hints

from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.core.async_utils import should_await
from aod._internal.application.port import Port
from aod._internal.core.application_exception import (
    InvalidUseCasePortFieldError,
)
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.event_emitter import Event, EventEmitter, get_active_events
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.core.base_guarded import inherit_context


def _resolve_port_class(tp: Any) -> type | None:
    if isinstance(tp, type):
        return tp
    origin = get_origin(tp)
    if origin is type:
        for arg in get_args(tp):
            if isinstance(arg, type):
                return arg
        return None
    if isinstance(origin, type):
        return origin
    return None


def _capture_events(fn: Callable[..., Any]) -> Callable[..., Any]:
    if iscoroutinefunction(fn):

        @wraps(fn)
        async def async_wrapper(self: BaseOperation, *args: Any, **kwargs: Any) -> Any:
            await self._begin_operation_dependencies_async()
            before = get_active_events()
            try:
                result = await fn(self, *args, **kwargs)
            except BaseException:
                after = get_active_events()
                if before is not None and after is not None:
                    self._set_events(after[len(before) :])
                await self._notify_failure_async()
                raise
            after = get_active_events()
            if before is not None and after is not None:
                self._set_events(after[len(before) :])
            await self._notify_async()
            return result

        return async_wrapper

    @wraps(fn)
    def wrapper(self: BaseOperation, *args: Any, **kwargs: Any) -> Any:
        self._begin_operation_dependencies()
        before = get_active_events()
        try:
            result = fn(self, *args, **kwargs)
        except BaseException:
            after = get_active_events()
            if before is not None and after is not None:
                self._set_events(after[len(before) :])
            self._notify_failure()
            raise
        after = get_active_events()
        if before is not None and after is not None:
            self._set_events(after[len(before) :])
        self._notify()
        return result

    return wrapper


class BaseOperation(BaseBehaviour):
    __skip_method_wrapping__: ClassVar[bool] = True
    __skip_port_check__: ClassVar[bool] = True
    __not_allowed_port_types__ = ()
    __allow_handler_ports__: ClassVar[bool] = False
    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)
    events: list[Event] = Field(default_factory=list, init=False)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @inherit_context
    def _set_events(self, events: list[Event]) -> None:
        self.events = events

    def _begin_operation_dependencies(self) -> None:
        begin_sessions = getattr(self, "_begin_sessions", None)
        if callable(begin_sessions):
            begin_sessions()
        for field_name in self.__model_fields__:
            value = object.__getattribute__(self, field_name)
            begin_sessions = getattr(value, "_begin_sessions", None)
            if callable(begin_sessions):
                begin_sessions()

    async def _begin_operation_dependencies_async(self) -> None:
        begin_sessions = getattr(self, "_begin_sessions_async", None)
        if callable(begin_sessions):
            await begin_sessions()
        for field_name in self.__model_fields__:
            value = object.__getattribute__(self, field_name)
            begin_sessions = getattr(value, "_begin_sessions_async", None)
            if callable(begin_sessions):
                await begin_sessions()

    def _operation_resources(
        self,
    ) -> tuple[list[Logger | AsyncLogger], list[EventBus | AsyncEventBus]]:
        loggers: list[Logger | AsyncLogger] = []
        event_buses: list[EventBus | AsyncEventBus] = []
        for field_name in self.__model_fields__:
            value = object.__getattribute__(self, field_name)
            if isinstance(value, (Logger, AsyncLogger)):
                loggers.append(value)
            if isinstance(value, (EventBus, AsyncEventBus)):
                event_buses.append(value)
        return loggers, event_buses

    def _notify(self) -> None:
        loggers, event_buses = self._operation_resources()
        for logger in loggers:
            logger.info(f"{type(self).__name__} events", events=self.events)
        for event_bus in event_buses:
            event_bus.publish(*self.events)
        for logger in loggers:
            logger.info(f"{type(self).__name__} completed")

    def _notify_failure(self) -> None:
        loggers, _ = self._operation_resources()
        for logger in loggers:
            logger.error(f"{type(self).__name__} failed with message")

    async def _notify_async(self) -> None:
        loggers, event_buses = self._operation_resources()
        for logger in loggers:
            await should_await(logger.info(f"{type(self).__name__} events", events=self.events))
        for event_bus in event_buses:
            await should_await(event_bus.publish(*self.events))
        for logger in loggers:
            await should_await(logger.info(f"{type(self).__name__} completed"))

    async def _notify_failure_async(self) -> None:
        loggers, _ = self._operation_resources()
        for logger in loggers:
            await should_await(logger.error(f"{type(self).__name__} failed with message"))

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        for method_name in ("run", "read", "write"):
            method = cls.__dict__.get(method_name)
            if (
                callable(method)
                and not getattr(method, "__isabstractmethod__", False)
                and not getattr(method, "__aod_events_wrapped__", False)
            ):
                wrapped = _capture_events(method)
                setattr(wrapped, "__aod_events_wrapped__", True)
                setattr(cls, method_name, wrapped)
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
            if issubclass(resolved, cls.__not_allowed_port_types__) or (
                getattr(resolved, "__aod_handler__", False)
                and not cls.__dict__.get("__allow_handler_ports__", False)
            ):
                raise InvalidUseCasePortFieldError(
                    field_name,
                    cls.__name__,
                    str(tp),
                )
