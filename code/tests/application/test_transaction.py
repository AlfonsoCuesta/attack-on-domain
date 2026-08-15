from __future__ import annotations

from typing import Any

import pytest
from aod._internal.application.event_bus import EventBus
from aod._internal.application.logger import Logger
from aod._internal.application.transaction import AsyncTransaction, Transaction, get_transaction
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.event_emitter import Event, EventEmitter
from aod._internal.core.fields.fields import PrivateField
from aod._internal.infrastructure.commit_context import _CommitContext
from aod._internal.infrastructure.session import AsyncSession, Session
from aod.testing.doubles import spy_port


class _Operation(BaseOperation):
    def run(self) -> None:
        pass


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
    operation = _Operation()

    with Transaction(operation=operation) as transaction:
        EventEmitter().emit(_Event(value="created"))

    assert operation.events[0].value == "created"
    assert transaction.events == operation.events


def test_transaction_context_is_available_only_inside_block() -> None:
    operation = _Operation()
    with pytest.raises(RuntimeError, match="No active transaction"):
        get_transaction()
    with Transaction(operation=operation):
        assert object.__getattribute__(get_transaction(), "operation") is operation
    with pytest.raises(RuntimeError, match="No active transaction"):
        get_transaction()


def test_transaction_commits_and_logs_and_publishes() -> None:
    operation = _Operation()
    session = _Session()
    logger = spy_port(Logger)()
    bus = spy_port(EventBus)()

    with Transaction(operation=operation, sessions=[session], loggers=[logger], event_buses=[bus]):
        EventEmitter().emit(_Event(value="created"))

    assert session._begun
    assert session._committed
    assert logger.info.call_count == 2
    assert bus.publish.call_count == 1


def test_transaction_rolls_back_and_preserves_events_on_failure() -> None:
    operation = _Operation()
    session = _Session()

    with pytest.raises(ValueError, match="boom"):
        with Transaction(operation=operation, sessions=[session]):
            EventEmitter().emit(_Event(value="before-failure"))
            raise ValueError("boom")

    assert session._rolled_back
    assert operation.events[0].value == "before-failure"


def test_transaction_rejects_nested_transactions() -> None:
    operation = _Operation()

    with Transaction(operation=operation):
        with pytest.raises(RuntimeError, match="cannot be nested"):
            with Transaction(operation=operation):
                pass


def test_transaction_resets_context_when_begin_fails() -> None:
    class FailingBegin(_Session):
        def begin(self) -> None:
            raise RuntimeError("begin failed")

    operation = _Operation()
    with pytest.raises(RuntimeError, match="begin failed"):
        with Transaction(operation=operation, sessions=[FailingBegin()]):
            pass
    with pytest.raises(RuntimeError, match="No active transaction"):
        get_transaction()


def test_transaction_rolls_back_when_commit_fails() -> None:
    class FailingCommit(_Session):
        def commit(self) -> None:
            raise RuntimeError("commit failed")

    session = FailingCommit()
    with pytest.raises(RuntimeError, match="commit failed"):
        with Transaction(operation=_Operation(), sessions=[session]):
            pass
    assert session._rolled_back


def test_transaction_commit_context_only_exists_during_commit() -> None:
    operation = _Operation()
    session = _Session()
    observed: list[bool] = []

    class TrackingSession(_Session):
        def commit(self) -> None:
            observed.append(_CommitContext.get(False))
            super().commit()

    session = TrackingSession()
    with Transaction(operation=operation, sessions=[session]):
        observed.append(_CommitContext.get(False))

    assert observed == [False, True]


def test_transaction_operation_can_supply_sessions_from_handler() -> None:
    session = _Session()

    class Handler:
        def _get_sessions(self) -> list[Session]:
            return [session]

    class Operation(BaseOperation):
        __skip_port_check__ = True
        handler: Any

        def run(self) -> None:
            pass

    operation = Operation(handler=Handler())
    with Transaction(operation=operation):
        pass

    assert session._begun
    assert session._committed


@pytest.mark.asyncio
async def test_async_transaction_commits_and_collects_events() -> None:
    operation = _Operation()
    session = _AsyncSession()

    async with AsyncTransaction(operation=operation, sessions=[session]):
        EventEmitter().emit(_Event(value="async"))

    assert session._begun
    assert session._committed
    assert operation.events[0].value == "async"


@pytest.mark.asyncio
async def test_async_transaction_rolls_back_on_failure() -> None:
    operation = _Operation()
    session = _AsyncSession()

    with pytest.raises(ValueError, match="boom"):
        async with AsyncTransaction(operation=operation, sessions=[session]):
            raise ValueError("boom")

    assert session._rolled_back


@pytest.mark.asyncio
async def test_async_transaction_logs_and_publishes() -> None:
    operation = _Operation()
    logger = spy_port(Logger)()
    bus = spy_port(EventBus)()
    async with AsyncTransaction(operation=operation, loggers=[logger], event_buses=[bus]):
        EventEmitter().emit(_Event(value="async"))
    assert logger.info.call_count == 2
    assert bus.publish.call_count == 1
