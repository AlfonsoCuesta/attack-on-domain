from __future__ import annotations

from abc import abstractmethod
from functools import wraps
from typing import Any, Callable, ClassVar

from aod._internal.application.event_bus import EventBus
from aod._internal.application.event_bus.async_ import EventBus as AsyncEventBus
from aod._internal.application.logger import Logger
from aod._internal.application.logger.async_ import Logger as AsyncLogger
from aod._internal.application.unit_of_work import UnitOfWork
from aod._internal.application.unit_of_work.async_ import UnitOfWork as AsyncUnitOfWork
from aod._internal.core.async_utils import should_await as awaiter
from aod._internal.core.base_guarded import inherit_context
from aod._internal.core.event_emitter import Event, EventCollector, EventEmitter
from aod._internal.core.fields.fields import Field, PrivateField

from .use_case import UseCase as SyncUseCase
from .use_case import _NullEventBus, _NullLogger, _NullUnitOfWork


class UseCase(SyncUseCase):
    __skip_method_wrapping__: ClassVar[bool] = True
    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)
    events: list[Event] = Field(default_factory=list, init=False)
    uow: UnitOfWork | AsyncUnitOfWork = Field(default_factory=_NullUnitOfWork)
    logger: Logger | AsyncLogger = Field(default_factory=_NullLogger)
    event_bus: EventBus | AsyncEventBus = Field(default_factory=_NullEventBus)

    @classmethod
    def _wrap_run_with_collector(cls, fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        async def wrapper(self: UseCase, *args: Any, **kwargs: Any) -> None:
            exception: BaseException | None = None

            with EventCollector() as events:
                try:
                    await awaiter(fn(self, *args, **kwargs))
                except BaseException as e:
                    exception = e

                self.events = list(events)

            await awaiter(self.logger.info(f"{type(self).__name__} events", events=self.events))

            if exception is not None:
                if self.uow.is_dirty:
                    await awaiter(self.uow.rollback())
                await awaiter(
                    self.logger.error(f"{type(self).__name__} failed with exception: {exception}")
                )
                raise exception

            if self.uow.is_dirty:
                try:
                    await awaiter(self.uow.commit())
                except BaseException:
                    await awaiter(self.uow.rollback())
                    await awaiter(self.logger.error(f"{type(self).__name__} commit failed"))
                    raise

            await awaiter(self.event_bus.publish(*self.events))
            await awaiter(
                self.logger.info(
                    f"{type(self).__name__} completed",
                    events=len(self.events),
                )
            )

        return wrapper

    @abstractmethod
    @inherit_context
    async def run(self) -> None: ...
