from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

from aod._internal.application.cache.cache_manager import get_cache_context
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.core.async_utils import should_await
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.event_emitter import Event, EventCollector, EventsListened
from aod._internal.core.fields import Field, PrivateField
from aod._internal.core.transaction_context import _active_transaction
from aod._internal.infrastructure.commit_context import commit_context
from aod._internal.infrastructure.session import AsyncSession, Session


class TransactionBase(BaseBehaviour):
    loggers: list[Logger | AsyncLogger] = Field(default_factory=list)
    event_buses: list[EventBus | AsyncEventBus] = Field(default_factory=list)
    _sessions: dict[int, Session | AsyncSession] = PrivateField(default_factory=dict)
    _events: list[Event] = PrivateField(default_factory=list)
    _collector: EventCollector | None = PrivateField(default=None)
    _listened: EventsListened | None = PrivateField(default=None)
    _token: Token[object | None] | None = PrivateField(default=None)

    @property
    def sessions(self) -> list[Session | AsyncSession]:
        return list(self._sessions.values())

    @property
    def events(self) -> list[Event]:
        return self._events

    def register_session(self, session: Session | AsyncSession) -> None:
        self._sessions.setdefault(id(session), session)

    def register_operation(self, operation: Any) -> None:
        for field_name in operation.__model_fields__:
            value = object.__getattribute__(operation, field_name)
            if isinstance(value, (Logger, AsyncLogger)) and value not in self.loggers:
                self.loggers.append(value)
            if isinstance(value, (EventBus, AsyncEventBus)) and value not in self.event_buses:
                self.event_buses.append(value)

    def _start(self) -> None:
        if _active_transaction.get() is not None:
            raise RuntimeError("Transactions cannot be nested")
        object.__setattr__(self, "_token", _active_transaction.set(self))

    def _finish_collection(self) -> None:
        if self._collector is not None:
            self._collector.__exit__(None, None, None)
        if self._listened is not None:
            object.__setattr__(self, "_events", list(self._listened))

    def _reset(self) -> None:
        for session in self.sessions:
            object.__setattr__(session, "_is_begun", False)
        if self._token is not None:
            _active_transaction.reset(self._token)
            object.__setattr__(self, "_token", None)

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
            logger.error(f"Transaction failed with message: {exception}")

    def _log_completion(self) -> None:
        for logger in self.loggers:
            logger.info("Transaction events", events=self._events)
        for bus in self.event_buses:
            bus.publish(*self._events)
        for logger in self.loggers:
            logger.info("Transaction completed")

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
            collector = EventCollector()
            object.__setattr__(self, "_collector", collector)
            object.__setattr__(self, "_listened", collector.__enter__())
        except Exception:
            self._reset()
            raise
        return self

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
            await should_await(logger.error(f"Transaction failed with message: {exception}"))

    async def _async_log_completion(self) -> None:
        for logger in self.loggers:
            await should_await(logger.info("Transaction events", events=self._events))
        for bus in self.event_buses:
            await should_await(bus.publish(*self._events))
        for logger in self.loggers:
            await should_await(logger.info("Transaction completed"))

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> bool:
        self._finish_collection()
        if exc_value is not None:
            try:
                await self._async_rollback_sessions()
                get_cache_context().discard()
                await self._async_log_failure(exc_value)
            finally:
                self._reset()
            return False
        try:
            await self._async_commit_sessions()
            await get_cache_context().flush_invalidations_async()
            await self._async_log_completion()
        except Exception as exception:
            try:
                await self._async_rollback_sessions()
                get_cache_context().discard()
                await self._async_log_failure(exception)
            finally:
                self._reset()
            raise
        finally:
            self._reset()
        return False


def get_transaction() -> TransactionBase:
    transaction = _active_transaction.get()
    if transaction is None:
        raise RuntimeError("No active transaction")
    return transaction  # type: ignore[return-value]


def get_active_transaction() -> TransactionBase | None:
    transaction = _active_transaction.get()
    return transaction  # type: ignore[return-value]
