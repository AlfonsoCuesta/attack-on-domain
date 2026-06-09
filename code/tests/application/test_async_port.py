from __future__ import annotations

import pytest
from aod._internal.core.event_emitter import Event
from aod.application.async_ import EventBus, Logger, UnitOfWork
from aod.testing.doubles.application.async_ import (
    SpyEventBus as AsyncSpyEventBus,
    SpyLogger as AsyncSpyLogger,
    SpyUnitOfWork as AsyncSpyUnitOfWork,
)


async def test_async_logger_concrete() -> None:
    log = AsyncSpyLogger()
    await log.info("hello", user_id=42)
    assert len(log.entries) == 1
    assert log.entries[0].msg == "hello"
    assert log.entries[0].context == {"user_id": 42}


async def test_async_logger_debug() -> None:
    log = AsyncSpyLogger()
    await log.debug("dbg", z=3)
    assert len(log.entries) == 1
    assert log.entries[0].level == "debug"
    assert log.entries[0].msg == "dbg"
    assert log.entries[0].context == {"z": 3}


async def test_async_logger_warning() -> None:
    log = AsyncSpyLogger()
    await log.warning("wrn", w=4)
    assert len(log.entries) == 1
    assert log.entries[0].level == "warning"
    assert log.entries[0].msg == "wrn"
    assert log.entries[0].context == {"w": 4}


async def test_async_logger_error() -> None:
    log = AsyncSpyLogger()
    await log.error("err", v=5)
    assert len(log.entries) == 1
    assert log.entries[0].level == "error"
    assert log.entries[0].msg == "err"
    assert log.entries[0].context == {"v": 5}


async def test_async_logger_is_abstract() -> None:
    with pytest.raises(TypeError):
        Logger()


async def test_async_event_bus_is_abstract() -> None:
    with pytest.raises(TypeError):
        EventBus()


async def test_async_event_bus_publish() -> None:
    bus = AsyncSpyEventBus()
    e1 = Event()
    e2 = Event()
    await bus.publish(e1, e2)
    assert len(bus.published) == 2


async def test_async_unit_of_work_is_abstract() -> None:
    with pytest.raises(TypeError):
        UnitOfWork()


async def test_async_unit_of_work_commit() -> None:
    uow = AsyncSpyUnitOfWork()
    await uow.commit()
    assert uow.committed


async def test_async_unit_of_work_rollback() -> None:
    uow = AsyncSpyUnitOfWork()
    await uow.rollback()
    assert uow.rolled_back


async def test_async_unit_of_work_flush() -> None:
    uow = AsyncSpyUnitOfWork()
    await uow.flush()
    assert uow.flushed