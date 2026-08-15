from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

from aod._internal.application.cache.cache_manager import get_cache_context
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.core.async_utils import should_await
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.event_emitter import Event, EventCollector, EventsListened
from aod._internal.core.fields import Field, PrivateField
from aod._internal.infrastructure.commit_context import commit_context
from aod._internal.infrastructure.session import AsyncSession, Session


_active_transaction: ContextVar[TransactionBase] = ContextVar("_active_transaction")


class TransactionBase(BaseBehaviour):
    sessions: list[Session | AsyncSession] = Field(default_factory=list)
    loggers: list[Logger | AsyncLogger] = Field(default_factory=list)
    event_buses: list[EventBus | AsyncEventBus] = Field(default_factory=list)
    operation: BaseOperation
    _events: list[Event] = PrivateField(default_factory=list)
    _collector: EventCollector | None = PrivateField(default=None)
    _listened: EventsListened | None = PrivateField(default=None)
    _token: Token[TransactionBase] | None = PrivateField(default=None)

    @property
    def operation_name(self) -> str:
        return type(self.operation).__name__

    @property
    def events(self) -> list[Event]:
        return self._events

    def _discover_sessions(self) -> list[Session | AsyncSession]:
        sessions = list(self.sessions)
        for field_name in self.operation.__model_fields__:
            value = object.__getattribute__(self.operation, field_name)
            get_sessions = getattr(value, "_get_sessions", None)
            if callable(get_sessions):
                sessions.extend(get_sessions())
        sessions.extend(getattr(self.operation, "_sessions", []))
        return list({id(session): session for session in sessions}.values())

    def _load_operation_ports(self) -> None:
        operation_loggers: list[Logger | AsyncLogger] = []
        operation_event_buses: list[EventBus | AsyncEventBus] = []
        for field_name in self.operation.__model_fields__:
            value = object.__getattribute__(self.operation, field_name)
            if isinstance(value, (Logger, AsyncLogger)):
                operation_loggers.append(value)
            elif isinstance(value, (EventBus, AsyncEventBus)):
                operation_event_buses.append(value)
        loggers = self.loggers + operation_loggers
        event_buses = self.event_buses + operation_event_buses
        object.__setattr__(self, "loggers", list({id(item): item for item in loggers}.values()))
        object.__setattr__(
            self,
            "event_buses",
            list({id(item): item for item in event_buses}.values()),
        )

    def _start(self) -> None:
        try:
            _active_transaction.get()
        except LookupError:
            pass
        else:
            raise RuntimeError("Transactions cannot be nested")
        object.__setattr__(self, "sessions", self._discover_sessions())
        self._load_operation_ports()
        object.__setattr__(self, "_token", _active_transaction.set(self))

    def _finish_collection(self) -> None:
        if self._collector is not None:
            self._collector.__exit__(None, None, None)
        if self._listened is not None:
            object.__setattr__(self, "_events", list(self._listened))
        object.__setattr__(self.operation, "events", self._events)

    def _reset(self) -> None:
        if self._token is not None:
            _active_transaction.reset(self._token)
            object.__setattr__(self, "_token", None)

    def _begin_sessions(self) -> None:
        for session in self.sessions:
            session.begin()

    def _commit_sessions(self) -> None:
        with commit_context():
            for session in self.sessions:
                if session.is_dirty():
                    session.commit()

    def _rollback_sessions(self) -> None:
        for session in self.sessions:
            if session.is_dirty():
                session.rollback()

    def _log_failure(self, exception: BaseException) -> None:
        for logger in self.loggers:
            logger.error(f"{self.operation_name} failed with message: {exception}")

    def _log_completion(self) -> None:
        for logger in self.loggers:
            logger.info(f"{self.operation_name} events", events=self._events)
        for bus in self.event_buses:
            bus.publish(*self._events)
        for logger in self.loggers:
            logger.info(f"{self.operation_name} completed")

    def _handle_failure(self, exception: BaseException) -> None:
        try:
            self._rollback_sessions()
            get_cache_context().discard()
            self._log_failure(exception)
        finally:
            self._reset()


class Transaction(TransactionBase):
    def __enter__(self) -> Transaction:
        self._start()
        try:
            self._begin_sessions()
            collector = EventCollector()
            object.__setattr__(self, "_collector", collector)
            object.__setattr__(self, "_listened", collector.__enter__())
        except Exception:
            self._reset()
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> bool:
        self._finish_collection()
        if exc_value is not None:
            self._handle_failure(exc_value)
            return False
        try:
            self._commit_sessions()
            get_cache_context().flush_invalidations()
            self._log_completion()
        except Exception as exception:
            self._handle_failure(exception)
            raise
        finally:
            self._reset()
        return False


class AsyncTransaction(TransactionBase):
    async def __aenter__(self) -> AsyncTransaction:
        self._start()
        try:
            await self._async_begin_sessions()
            collector = EventCollector()
            object.__setattr__(self, "_collector", collector)
            object.__setattr__(self, "_listened", collector.__enter__())
        except Exception:
            self._reset()
            raise
        return self

    async def _async_begin_sessions(self) -> None:
        for session in self.sessions:
            await should_await(session.begin())

    async def _async_commit_sessions(self) -> None:
        with commit_context():
            for session in self.sessions:
                if session.is_dirty():
                    await should_await(session.commit())

    async def _async_rollback_sessions(self) -> None:
        for session in self.sessions:
            if session.is_dirty():
                await should_await(session.rollback())

    async def _async_log_failure(self, exception: BaseException) -> None:
        for logger in self.loggers:
            await should_await(
                logger.error(f"{self.operation_name} failed with exception: {exception}")
            )

    async def _async_log_completion(self) -> None:
        for logger in self.loggers:
            await should_await(logger.info(f"{self.operation_name} events", events=self._events))
        for bus in self.event_buses:
            await should_await(bus.publish(*self._events))
        for logger in self.loggers:
            await should_await(logger.info(f"{self.operation_name} completed"))

    async def _async_handle_failure(self, exception: BaseException) -> None:
        try:
            await self._async_rollback_sessions()
            get_cache_context().discard()
            await self._async_log_failure(exception)
        finally:
            self._reset()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> bool:
        self._finish_collection()
        if exc_value is not None:
            await self._async_handle_failure(exc_value)
            return False
        try:
            await self._async_commit_sessions()
            await get_cache_context().flush_invalidations_async()
            await self._async_log_completion()
        except Exception as exception:
            await self._async_handle_failure(exception)
            raise
        finally:
            self._reset()
        return False


def get_transaction() -> TransactionBase:
    try:
        return _active_transaction.get()
    except LookupError:
        raise RuntimeError("No active transaction") from None
