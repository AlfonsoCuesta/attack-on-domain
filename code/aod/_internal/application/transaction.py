from __future__ import annotations

from contextvars import Token
from typing import Any, cast

from aod._internal.core.async_utils import should_await
from aod._internal.application.cache.cache_manager import get_cache_context
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.event_emitter import Event, EventCollector, EventsListened
from aod._internal.core.fields import PrivateField
from aod._internal.core.transaction_context import _active_transaction, TransactionContext
from aod._internal.infrastructure.commit_context import commit_context
from aod._internal.infrastructure.session import AsyncSession, Session


class TransactionBase(BaseBehaviour):
    _sessions: dict[int, Session | AsyncSession] = PrivateField(default_factory=dict)
    _events: list[Event] = PrivateField(default_factory=list)
    _collector: EventCollector | None = PrivateField(default=None)
    _listened: EventsListened | None = PrivateField(default=None)
    _token: Token[TransactionContext | None] | None = PrivateField(default=None)

    @property
    def sessions(self) -> list[Session | AsyncSession]:
        return list(self._sessions.values())

    @property
    def events(self) -> list[Event]:
        return self._events

    def register_session(self, session: object) -> None:
        if not isinstance(session, (Session, AsyncSession)):
            raise TypeError(f"Expected a session, got {type(session).__name__}")
        self._sessions.setdefault(id(session), session)

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
            session._reset_begin()
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

    def _handle_failure(self) -> None:
        try:
            self._rollback_sessions()
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
            self._handle_failure()
            return False
        try:
            self._commit_sessions()
            get_cache_context().flush_invalidations()
        except Exception:
            self._handle_failure()
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
            finally:
                self._reset()
            return False
        try:
            await self._async_commit_sessions()
            await get_cache_context().flush_invalidations_async()
        except Exception:
            try:
                await self._async_rollback_sessions()
                get_cache_context().discard()
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
    return cast(TransactionBase, transaction)


def get_active_transaction() -> TransactionBase | None:
    transaction = _active_transaction.get()
    return cast(TransactionBase | None, transaction)
