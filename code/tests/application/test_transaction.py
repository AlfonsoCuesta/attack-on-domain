from __future__ import annotations

import pytest
from aod._internal.application.transaction import AsyncTransaction, Transaction, get_transaction
from aod._internal.core.event_emitter import Event, EventEmitter
from aod._internal.core.fields.fields import PrivateField
from aod._internal.infrastructure.commit_context import _CommitContext
from aod._internal.infrastructure.session import AsyncSession, Session


class _Event(Event):
    value: str


class _Session(Session):
    _begun: bool = PrivateField(default=False)
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)

    def begin(self) -> None:
        self._begun = True

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        self._rolled_back = True

    def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return True

    def execute(self, operation: object) -> object:
        return operation

    def query(self, operation: object) -> object:
        return operation


class _AsyncSession(AsyncSession):
    _begun: bool = PrivateField(default=False)
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)

    async def begin(self) -> None:
        self._begun = True

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        self._rolled_back = True

    async def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return True

    async def execute(self, operation: object) -> object:
        return operation

    async def query(self, operation: object) -> object:
        return operation


def test_transaction_collects_events_and_updates_operation() -> None:
    with Transaction() as transaction:
        EventEmitter().emit(_Event(value="created"))

    assert transaction.events[0].value == "created"


def test_transaction_context_is_available_only_inside_block() -> None:
    with pytest.raises(RuntimeError, match="No active transaction"):
        get_transaction()
    with Transaction():
        assert isinstance(get_transaction(), Transaction)
    with pytest.raises(RuntimeError, match="No active transaction"):
        get_transaction()


def test_transaction_commits_registered_sessions() -> None:
    session = _Session()

    with Transaction():
        session._begin()
        EventEmitter().emit(_Event(value="created"))

    assert session._begun
    assert session._committed


def test_transaction_rolls_back_and_preserves_events_on_failure() -> None:
    session = _Session()

    with pytest.raises(ValueError, match="boom"):
        with Transaction() as transaction:
            session._begin()
            EventEmitter().emit(_Event(value="before-failure"))
            raise ValueError("boom")

    assert session._rolled_back
    assert transaction.events[0].value == "before-failure"


def test_transaction_rejects_nested_transactions() -> None:
    with Transaction():
        with pytest.raises(RuntimeError, match="cannot be nested"):
            with Transaction():
                pass


def test_transaction_resets_context_when_begin_fails() -> None:
    class FailingBegin(_Session):
        def begin(self) -> None:
            raise RuntimeError("begin failed")

    session = FailingBegin()
    with Transaction():
        with pytest.raises(RuntimeError, match="begin failed"):
            session._begin()
        assert not session._is_begun
    with pytest.raises(RuntimeError, match="No active transaction"):
        get_transaction()


def test_begin_is_idempotent_and_registers_the_session_once() -> None:
    session = _Session()

    with Transaction() as transaction:
        session._begin()
        session._begin()

    assert transaction.sessions == [session]
    assert session._committed


def test_already_begun_session_is_registered_in_a_new_transaction() -> None:
    session = _Session()
    session._begin()

    with Transaction() as transaction:
        session._begin()

    assert transaction.sessions == [session]
    assert session._committed


def test_transaction_rolls_back_when_commit_fails() -> None:
    class FailingCommit(_Session):
        def commit(self) -> None:
            raise RuntimeError("commit failed")

    session = FailingCommit()
    with pytest.raises(RuntimeError, match="commit failed"):
        with Transaction():
            session._begin()
    assert session._rolled_back


def test_transaction_commit_context_only_exists_during_commit() -> None:
    session = _Session()
    observed: list[bool] = []

    class TrackingSession(_Session):
        def commit(self) -> None:
            observed.append(_CommitContext.get(False))
            super().commit()

    session = TrackingSession()
    with Transaction():
        session._begin()
        observed.append(_CommitContext.get(False))

    assert observed == [False, True]


@pytest.mark.asyncio
async def test_async_transaction_commits_and_collects_events() -> None:
    session = _AsyncSession()

    async with AsyncTransaction() as transaction:
        await session._begin()
        await session.execute("operation")
        EventEmitter().emit(_Event(value="async"))

    assert session._begun
    assert session._committed
    assert transaction.events[0].value == "async"


@pytest.mark.asyncio
async def test_async_transaction_rolls_back_on_failure() -> None:
    session = _AsyncSession()

    with pytest.raises(ValueError, match="boom"):
        async with AsyncTransaction():
            await session._begin()
            raise ValueError("boom")

    assert session._rolled_back
