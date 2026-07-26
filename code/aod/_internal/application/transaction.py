from __future__ import annotations

from typing import Any, Callable

from aod._internal.application.cache.cache_manager import get_cache_context
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.core.async_utils import should_await
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.event_emitter import Event, EventCollector
from aod._internal.core.fields import Field, PrivateField
from aod._internal.infrastructure.commit_context import commit_context
from aod._internal.infrastructure.session import AsyncSession, Session


class TransactionBase(BaseBehaviour):
    sessions: list[Session | AsyncSession] = Field(default_factory=list)
    loggers: list[Logger | AsyncLogger] = Field(default_factory=list)
    event_buses: list[EventBus | AsyncEventBus] = Field(default_factory=list)
    only_read: bool = Field(default=False)
    operation: BaseOperation
    _events: list[Event] = PrivateField(default_factory=list)

    @property
    def operation_name(self) -> str:
        return type(self.operation).__name__

    def add_session(self, session: Session | AsyncSession) -> None:
        self.sessions.append(session)

    def add_logger(self, logger: Logger | AsyncLogger) -> None:
        self.loggers.append(logger)

    def add_event_bus(self, event_bus: EventBus | AsyncEventBus) -> None:
        self.event_buses.append(event_bus)

    def get_events(self) -> list[Event]:
        return self._events


class Transaction(TransactionBase):
    def run_transaction(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        cache_ctx = get_cache_context()
        cached = cache_ctx.get(self.operation)
        if cached is not None:
            return cached

        exception: Exception | None = None
        if not self.only_read:
            self._begin_sessions()

        with EventCollector() as events:
            try:
                result = fn(*args, **kwargs)
            except Exception as e:
                exception = e
            self._events = list(events)

        if exception is not None:
            self._handle_operation_failure(exception)

        try:
            self._commit_and_publish()
        except Exception as e:
            self._handle_operation_failure(e)

        cache_ctx.set(self.operation, result)
        cache_ctx.delete(self.operation)
        cache_ctx.flush()

        return result

    def _begin_sessions(self) -> None:
        for session in self.sessions:
            session.begin()

    def _commit_and_publish(self) -> None:
        if not self.only_read:
            self._commit_sessions()
        self._log_transaction_completion()

    def _commit_sessions(self) -> None:
        with commit_context():
            for session in self.sessions:
                if session.is_dirty():
                    session.commit()

    def _handle_operation_failure(self, exception: Exception) -> None:
        if not self.only_read:
            for session in self.sessions:
                if session.is_dirty():
                    session.rollback()
        cache_ctx = get_cache_context()
        cache_ctx.discard()
        for logger in self.loggers:
            logger.error(f"{self.operation_name} failed with message: {exception}")
        raise exception

    def _log_transaction_completion(self) -> None:
        for logger in self.loggers:
            logger.info(f"{self.operation_name} events", events=self._events)
        for bus in self.event_buses:
            bus.publish(*self._events)
        for logger in self.loggers:
            logger.info(f"{self.operation_name} completed")


class AsyncTransaction(TransactionBase):
    async def run_transaction(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        cache_ctx = get_cache_context()
        cached = await cache_ctx.get_async(self.operation)
        if cached is not None:
            return cached

        exception: Exception | None = None
        if not self.only_read:
            await self._begin_sessions()

        with EventCollector() as events:
            try:
                result = await should_await(fn(*args, **kwargs))
            except Exception as e:
                exception = e
            self._events = list(events)

        if exception is not None:
            await self._handle_operation_failure(exception)

        try:
            await self._commit_and_publish()
        except Exception as e:
            await self._handle_operation_failure(e)

        cache_ctx.set(self.operation, result)
        cache_ctx.delete(self.operation)
        await cache_ctx.flush_async()

        return result

    async def _begin_sessions(self) -> None:
        for session in self.sessions:
            await should_await(session.begin())

    async def _handle_operation_failure(self, exception: Exception) -> None:
        if not self.only_read:
            await self._rollback()
        cache_ctx = get_cache_context()
        cache_ctx.discard()
        for logger in self.loggers:
            await should_await(
                logger.error(f"{self.operation_name} failed with exception: {exception}")
            )
        raise exception

    async def _commit_and_publish(self) -> None:
        if not self.only_read:
            await self._commit_sessions()
        await self._log_transaction_completion()

    async def _commit_sessions(self) -> None:
        with commit_context():
            for session in self.sessions:
                if session.is_dirty():
                    await should_await(session.commit())

    async def _rollback(self) -> None:
        for session in self.sessions:
            if session.is_dirty():
                await should_await(session.rollback())

    async def _log_transaction_completion(self) -> None:
        for logger in self.loggers:
            await should_await(logger.info(f"{self.operation_name} events", events=self._events))
        for bus in self.event_buses:
            await should_await(bus.publish(*self._events))
        for logger in self.loggers:
            await should_await(logger.info(f"{self.operation_name} completed"))
