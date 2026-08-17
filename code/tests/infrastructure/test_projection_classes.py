from __future__ import annotations

import pytest
from aod._internal.application.event_bus import EventBus
from aod._internal.application.logger import Logger
from aod._internal.application.transaction import AsyncTransaction, Transaction
from aod._internal.core.event_emitter import Event
from aod._internal.core.fields.fields import PrivateField
from aod._internal.infrastructure.projection import (
    AsyncReadProjection,
    AsyncWriteProjection,
    Projection,
    ReadProjection,
    WriteProjection,
)
from aod._internal.infrastructure.session import AsyncSession, Session
from aod.testing.doubles import spy_port


class _Event(Event):
    value: str


class _Session(Session):
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)

    def begin(self) -> None:
        pass

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
    _committed: bool = PrivateField(default=False)

    async def begin(self) -> None:
        pass

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return True

    async def execute(self, operation: object) -> object:
        return operation

    async def query(self, operation: object) -> object:
        return operation


def test_read_projection_without_transaction_does_not_collect_events() -> None:
    class Read(ReadProjection):
        def read(self) -> str:
            self._event_emitter.emit(_Event(value="read"))
            return "ok"

    projection = Read()
    assert projection.read() == "ok"
    assert projection.events == []


def test_write_projection_uses_transaction() -> None:
    class Write(WriteProjection):
        def write(self) -> str:
            self._event_emitter.emit(_Event(value="write"))
            return "ok"

    projection = Write()
    with Transaction():
        assert projection.write() == "ok"
    assert len(projection.events) == 1


def test_projection_sessions_are_discovered() -> None:
    session = _Session()

    class Write(WriteProjection):
        session: _Session

        def write(self) -> None:
            pass

    projection = Write(session=session)
    with Transaction():
        projection.write()
    assert session._committed
    assert not session._is_begun


def test_projection_uses_logger_and_event_bus() -> None:
    class Read(ReadProjection):
        logger: Logger
        event_bus: EventBus

        def read(self) -> None:
            self._event_emitter.emit(_Event(value="read"))

    logger = spy_port(Logger)()
    bus = spy_port(EventBus)()
    projection = Read(logger=logger, event_bus=bus)
    with Transaction():
        projection.read()
    assert logger.info.call_count == 2
    assert bus.publish.call_count == 1


@pytest.mark.asyncio
async def test_async_read_projection_uses_async_transaction() -> None:
    class Read(AsyncReadProjection):
        async def read(self) -> str:
            self._event_emitter.emit(_Event(value="read"))
            return "ok"

    projection = Read()
    async with AsyncTransaction():
        assert await projection.read() == "ok"
    assert len(projection.events) == 1


@pytest.mark.asyncio
async def test_async_write_projection_discovers_session() -> None:
    session = _AsyncSession()

    class Write(AsyncWriteProjection):
        session: _AsyncSession

        async def write(self) -> None:
            pass

    projection = Write(session=session)
    async with AsyncTransaction():
        await projection.write()
    assert session._committed
    assert not session._is_begun


def test_combined_projection_stays_unwrapped() -> None:
    class Both(Projection):
        def read(self) -> str:
            return "read"

        def write(self) -> str:
            return "write"

    projection = Both()
    assert projection.read() == "read"
    assert projection.write() == "write"
