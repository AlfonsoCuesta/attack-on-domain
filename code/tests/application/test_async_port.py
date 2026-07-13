from __future__ import annotations

import pytest
from aod._internal.core.event_emitter import Event
from aod._internal.application.unit_of_work import AsyncUnitOfWork as UnitOfWork
from aod.application.async_ import EventBus, Logger
from aod.testing.doubles import port_stub


async def test_async_logger_concrete() -> None:
    log = port_stub(Logger)()
    await log.info("hello", user_id=42)
    assert log.info.call_count == 1
    assert log.info.call_args_list[0].args == ("hello",)
    assert log.info.call_args_list[0].kwargs == {"user_id": 42}


async def test_async_logger_debug() -> None:
    log = port_stub(Logger)()
    await log.debug("dbg", z=3)
    assert log.debug.call_count == 1
    assert log.debug.call_args_list[0].args == ("dbg",)
    assert log.debug.call_args_list[0].kwargs == {"z": 3}


async def test_async_logger_warning() -> None:
    log = port_stub(Logger)()
    await log.warning("wrn", w=4)
    assert log.warning.call_count == 1
    assert log.warning.call_args_list[0].args == ("wrn",)
    assert log.warning.call_args_list[0].kwargs == {"w": 4}


async def test_async_logger_error() -> None:
    log = port_stub(Logger)()
    await log.error("err", v=5)
    assert log.error.call_count == 1
    assert log.error.call_args_list[0].args == ("err",)
    assert log.error.call_args_list[0].kwargs == {"v": 5}


async def test_async_logger_is_abstract() -> None:
    with pytest.raises(TypeError):
        Logger()


async def test_async_event_bus_is_abstract() -> None:
    with pytest.raises(TypeError):
        EventBus()


async def test_async_event_bus_publish() -> None:
    bus = port_stub(EventBus)()
    e1 = Event()
    e2 = Event()
    await bus.publish(e1, e2)
    assert bus.publish.call_count == 1
    assert len(bus.publish.call_args_list[0].args) == 2


async def test_async_unit_of_work_commit() -> None:
    uow = port_stub(UnitOfWork)()
    await uow.commit()
    assert uow.commit.called


async def test_async_unit_of_work_rollback() -> None:
    uow = port_stub(UnitOfWork)()
    await uow.rollback()
    assert uow.rollback.called
