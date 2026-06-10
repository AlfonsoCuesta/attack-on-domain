from __future__ import annotations

from abc import abstractmethod
from functools import wraps
from typing import Any, Callable

from aod._internal.application.unit_of_work import AsyncUnitOfWork, UnitOfWork
from aod._internal.application.unit_of_work.null_unit_of_work import NullUnitOfWork
from aod._internal.core.async_utils import should_await
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.event_emitter import EventCollector
from aod._internal.core.fields.fields import Field

_USE_CASE_WRAPPED_KEY = "__aod_use_case_wrapped__"


class UseCase(BaseOperation):
    __skip_port_check__ = True
    uow: UnitOfWork = Field(default_factory=NullUnitOfWork)

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
                    result = fn(self, *args, **kwargs)
                except BaseException as e:
                    exception = e

                self.events = list(events)

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

            self.logger.info(f"{type(self).__name__} events", events=self.events)
            self.cache.flush()
            self.event_bus.publish(*self.events)
            self.logger.info(f"{type(self).__name__} completed")
            return result

        return wrapper

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any: ...


class AsyncUseCase(BaseOperation):
    __skip_port_check__ = True
    uow: UnitOfWork | AsyncUnitOfWork = Field(default_factory=NullUnitOfWork)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_run: Callable[..., Any] | None = cls.__dict__.get("run")
        if original_run is not None and not getattr(original_run, _USE_CASE_WRAPPED_KEY, False):
            wrapped = cls._wrap_run_with_collector(original_run)
            setattr(cls, "run", wrapped)
            setattr(wrapped, _USE_CASE_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)

    @classmethod
    def _wrap_run_with_collector(cls, fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        async def wrapper(self: AsyncUseCase, *args: Any, **kwargs: Any) -> None:
            exception: BaseException | None = None

            with EventCollector() as events:
                try:
                    await should_await(fn(self, *args, **kwargs))
                except BaseException as e:
                    exception = e

                self.events = list(events)

            if exception is not None:
                await should_await(self.uow.rollback())
                await should_await(
                    self.logger.error(f"{type(self).__name__} failed with exception: {exception}")
                )
                raise exception

            try:
                await should_await(self.uow.commit())
            except BaseException:
                await should_await(self.uow.rollback())
                await should_await(self.logger.error(f"{type(self).__name__} commit failed"))
                raise

            await should_await(
                self.logger.info(f"{type(self).__name__} events", events=self.events)
            )
            await should_await(self.cache.flush())
            await should_await(self.event_bus.publish(*self.events))
            await should_await(self.logger.info(f"{type(self).__name__} completed"))

        return wrapper

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any: ...
