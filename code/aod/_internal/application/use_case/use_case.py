from __future__ import annotations

from abc import abstractmethod
from functools import wraps
from typing import Any, Callable

from aod._internal.application.transaction import AsyncTransaction, Transaction
from aod._internal.core.async_utils import should_await
from aod._internal.core.base_operation import BaseOperation
from aod._internal.infrastructure.handlers.handlers import BaseHandler
from aod._internal.infrastructure.session import AsyncSession, Session

_USE_CASE_WRAPPED_KEY = "__aod_use_case_wrapped__"


class UseCase(BaseOperation):
    __skip_port_check__ = True
    __not_allowed_port_types__ = (Session, AsyncSession)

    def _build_tx(self) -> Transaction:
        tx = Transaction(operation=self)
        for logger in self._loggers:
            tx.add_logger(logger)
        for bus in self._event_buses:
            tx.add_event_bus(bus)
        for field_name in self.__model_fields__:
            value = object.__getattribute__(self, field_name)
            if isinstance(value, BaseHandler):
                for session in value._get_sessions():
                    tx.add_session(session)
        return tx

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
        def wrapper(self: UseCase, *args: Any, **kwargs: Any) -> Any:
            tx = self._build_tx()
            try:
                result = tx.run_transaction(fn, self, *args, **kwargs)
            finally:
                self.events = tx.get_events()
            return result

        return wrapper

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any: ...


class AsyncUseCase(BaseOperation):
    __skip_port_check__ = True
    __not_allowed_port_types__ = (Session, AsyncSession)

    def _build_tx(self) -> AsyncTransaction:
        tx = AsyncTransaction(operation=self)
        for logger in self._loggers:
            tx.add_logger(logger)
        for bus in self._event_buses:
            tx.add_event_bus(bus)
        for field_name in self.__model_fields__:
            value = object.__getattribute__(self, field_name)
            if isinstance(value, BaseHandler):
                for session in value._get_sessions():
                    tx.add_session(session)
        return tx

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
        async def wrapper(self: AsyncUseCase, *args: Any, **kwargs: Any) -> Any:
            tx = self._build_tx()
            try:
                result = await should_await(tx.run_transaction(fn, self, *args, **kwargs))
            finally:
                self.events = tx.get_events()
            return result

        return wrapper

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any: ...
