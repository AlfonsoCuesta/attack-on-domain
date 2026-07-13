from __future__ import annotations

from abc import abstractmethod
from functools import wraps
from typing import Any, Callable

from aod._internal.application.unit_of_work import AsyncUnitOfWork, UnitOfWork
from aod._internal.core.async_utils import should_await
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.event_emitter import EventCollector
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.infrastructure.handlers.handlers import BaseHandler
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.infrastructure.unit_of_work import AsyncUnitOfWork as InfraAsyncUnitOfWork
from aod._internal.infrastructure.unit_of_work import UnitOfWork as InfraUnitOfWork

_USE_CASE_WRAPPED_KEY = "__aod_use_case_wrapped__"


class UseCase(BaseOperation):
    __skip_port_check__ = True
    __not_allowed_port_types__ = (Session, AsyncSession)
    _uow: UnitOfWork = PrivateField(default_factory=InfraUnitOfWork)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._register_handlers()

    def _register_handlers(self) -> None:
        for field_name in self.__model_fields__:
            value = object.__getattribute__(self, field_name)
            if isinstance(value, BaseHandler):
                self._uow.add_handler(value)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_run: Callable[..., Any] | None = cls.__dict__.get("run")
        if original_run is not None and not getattr(original_run, _USE_CASE_WRAPPED_KEY, False):
            wrapped = cls._wrap_run_with_collector(original_run)
            setattr(cls, "run", wrapped)
            setattr(wrapped, _USE_CASE_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)

    @staticmethod
    def _wrap_run_with_collector(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(self: UseCase, *args: Any, **kwargs: Any) -> None:
            exception: BaseException | None = None

            self._uow.begin()
            with EventCollector() as events:
                try:
                    result = fn(self, *args, **kwargs)
                except BaseException as e:
                    exception = e

                self.events = list(events)

            if exception is not None:
                self._uow.rollback()
                for logger in self._loggers:
                    logger.error(f"{type(self).__name__} failed with exception: {exception}")
                raise exception

            try:
                self._uow.commit()
            except BaseException:
                self._uow.rollback()
                for logger in self._loggers:
                    logger.error(f"{type(self).__name__} commit failed")
                raise

            for logger in self._loggers:
                logger.info(f"{type(self).__name__} events", events=self.events)
            for bus in self._event_buses:
                bus.publish(*self.events)
            for logger in self._loggers:
                logger.info(f"{type(self).__name__} completed")
            return result

        return wrapper

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any: ...


class AsyncUseCase(BaseOperation):
    __skip_port_check__ = True
    __not_allowed_port_types__ = (Session, AsyncSession)
    _uow: UnitOfWork | AsyncUnitOfWork = Field(default_factory=InfraAsyncUnitOfWork)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._register_handlers()

    def _register_handlers(self) -> None:
        for field_name in self.__model_fields__:
            value = object.__getattribute__(self, field_name)
            if isinstance(value, BaseHandler):
                self._uow.add_handler(value)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_run: Callable[..., Any] | None = cls.__dict__.get("run")
        if original_run is not None and not getattr(original_run, _USE_CASE_WRAPPED_KEY, False):
            wrapped = cls._wrap_run_with_collector(original_run)
            setattr(cls, "run", wrapped)
            setattr(wrapped, _USE_CASE_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)

    @staticmethod
    def _wrap_run_with_collector(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        async def wrapper(self: AsyncUseCase, *args: Any, **kwargs: Any) -> None:
            exception: BaseException | None = None

            await should_await(self._uow.begin())
            with EventCollector() as events:
                try:
                    result = await should_await(fn(self, *args, **kwargs))
                except BaseException as e:
                    exception = e

                self.events = list(events)

            if exception is not None:
                await should_await(self._uow.rollback())
                for logger in self._loggers:
                    await should_await(
                        logger.error(f"{type(self).__name__} failed with exception: {exception}")
                    )
                raise exception

            try:
                await should_await(self._uow.commit())
            except BaseException:
                await should_await(self._uow.rollback())
                for logger in self._loggers:
                    await should_await(logger.error(f"{type(self).__name__} commit failed"))
                raise

            for logger in self._loggers:
                await should_await(logger.info(f"{type(self).__name__} events", events=self.events))
            for bus in self._event_buses:
                await should_await(bus.publish(*self.events))
            for logger in self._loggers:
                await should_await(logger.info(f"{type(self).__name__} completed"))
            return result

        return wrapper

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any: ...
