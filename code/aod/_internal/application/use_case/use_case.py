from __future__ import annotations

from abc import abstractmethod
from functools import wraps
from typing import Any, Callable, ClassVar

from aod._internal.application.event_bus import EventBus
from aod._internal.application.logger import Logger
from aod._internal.application.unit_of_work import UnitOfWork
from aod._internal.core.base_guarded import inherit_context
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.event_emitter import Event, EventCollector, EventEmitter
from aod._internal.core.fields.fields import Field, PrivateField

_USE_CASE_WRAPPED_KEY = "__aod_use_case_wrapped__"


class _NullLogger(Logger):
    def debug(self, msg: str, **context: object) -> None: ...
    def info(self, msg: str, **context: object) -> None: ...
    def warning(self, msg: str, **context: object) -> None: ...
    def error(self, msg: str, **context: object) -> None: ...


class _NullEventBus(EventBus):
    def publish(self, *events: Event) -> None: ...


class _NullUnitOfWork(UnitOfWork):
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def flush(self) -> None: ...


class UseCase(BaseSealed):
    __skip_method_wrapping__: ClassVar[bool] = True
    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)
    events: list[Event] = Field(default_factory=list, init=False)
    uow: UnitOfWork = Field(default_factory=_NullUnitOfWork)
    logger: Logger = Field(default_factory=_NullLogger)
    event_bus: EventBus = Field(default_factory=_NullEventBus)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_run: Callable[..., None] | None = cls.__dict__.get("run")
        if original_run is not None and not getattr(original_run, _USE_CASE_WRAPPED_KEY, False):
            wrapped = cls._wrap_run_with_collector(original_run)
            setattr(cls, "run", wrapped)
            setattr(wrapped, _USE_CASE_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)

    @staticmethod
    def _wrap_run_with_collector(fn: Callable[..., None]) -> Callable[..., None]:
        @wraps(fn)
        def wrapper(self: UseCase, *args: Any, **kwargs: Any) -> None:
            exception: BaseException | None = None

            with EventCollector() as events:
                try:
                    fn(self, *args, **kwargs)
                except BaseException as e:
                    exception = e

                self.events = list(events)

            self.logger.info(f"{type(self).__name__} events", events=len(self.events))

            if exception is not None:
                self.uow.rollback()
                self.logger.error(f"{type(self).__name__} failed with exception: {exception}")
                raise exception

            try:
                self.uow.commit()
            except BaseException:
                self.uow.rollback()
                self.logger.error(f"{type(self).__name__} commit failed")
                raise

            self.event_bus.publish(*self.events)
            self.logger.info(
                f"{type(self).__name__} completed",
                events=len(self.events),
            )

        return wrapper

    @abstractmethod
    @inherit_context
    def run(self) -> None: ...
