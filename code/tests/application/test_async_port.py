from __future__ import annotations

from typing import Generic, TypeVar

import pytest
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.event_emitter import Event
from aod._internal.domain.entity import RootEntity
from aod.application import Command, Query
from aod.application.event_bus.async_ import EventBus as AsyncEventBus
from aod.application.logger.async_ import Logger as AsyncLogger
from aod.application.unit_of_work.async_ import UnitOfWork as AsyncUnitOfWork
from aod.testing.doubles import (
    AsyncSpyEventBus,
    AsyncSpyLogger,
    AsyncSpyUnitOfWork,
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
        AsyncLogger()  # type: ignore[abstract]


async def test_async_event_bus_is_abstract() -> None:
    with pytest.raises(TypeError):
        AsyncEventBus()  # type: ignore[abstract]


async def test_async_event_bus_publish() -> None:
    bus = AsyncSpyEventBus()
    e1 = Event()
    e2 = Event()
    await bus.publish(e1, e2)
    assert len(bus.published) == 2


async def test_async_unit_of_work_is_abstract() -> None:
    with pytest.raises(TypeError):
        AsyncUnitOfWork()  # type: ignore[abstract]


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


class User(RootEntity):
    id: int
    name: str


T = TypeVar("T")


class CreateUser(Command[User, User]):
    name: str


class GetUser(Query[User, User | None]):
    user_id: int


class AsyncSpyRepo(Generic[T]):
    def __init__(self) -> None:
        self.commands: list[Command] = []
        self.queries: list[Query] = []

    async def command(self, cmd: Command) -> object:
        self.commands.append(cmd)
        if isinstance(cmd, CreateUser):
            return User(id=1, name=cmd.name)
        return None

    async def query(self, query: Query) -> object:
        self.queries.append(query)
        if isinstance(query, GetUser) and query.user_id == 1:
            return User(id=1, name="Alice")
        return None


class AsyncSpyUserRepo(AsyncSpyRepo[User]):
    pass


async def test_async_unit_of_work_dispatch_command() -> None:
    repo = AsyncSpyUserRepo()
    uow = AsyncSpyUnitOfWork(repositories=[repo])
    result = await uow.command(CreateUser(name="Bob"))
    assert isinstance(result, User)
    assert result.name == "Bob"
    assert len(repo.commands) == 1


async def test_async_unit_of_work_is_dirty_after_command() -> None:
    repo = AsyncSpyUserRepo()
    uow = AsyncSpyUnitOfWork(repositories=[repo])
    assert not uow.is_dirty
    await uow.command(CreateUser(name="Bob"))
    assert uow.is_dirty


async def test_async_unit_of_work_is_dirty_false_after_query_only() -> None:
    repo = AsyncSpyUserRepo()
    uow = AsyncSpyUnitOfWork(repositories=[repo])
    await uow.query(GetUser(user_id=1))
    assert not uow.is_dirty


async def test_async_unit_of_work_dispatch_query() -> None:
    repo = AsyncSpyUserRepo()
    uow = AsyncSpyUnitOfWork(repositories=[repo])
    result = await uow.query(GetUser(user_id=1))
    assert isinstance(result, User)
    assert result.name == "Alice"
    assert len(repo.queries) == 1


async def test_async_unit_of_work_unknown_entity_raises() -> None:
    class OtherEntity(RootEntity):
        id: int

    class OtherCommand(Command[OtherEntity, None]):
        pass

    repo = AsyncSpyUserRepo()
    uow = AsyncSpyUnitOfWork(repositories=[repo])
    with pytest.raises(DomainException, match="No repository registered for entity OtherEntity"):
        await uow.command(OtherCommand())


async def test_async_unit_of_work_empty_repositories_raises() -> None:
    uow = AsyncSpyUnitOfWork()
    with pytest.raises(DomainException, match="No repository registered for entity User"):
        await uow.command(CreateUser(name="X"))


async def test_async_unit_of_work_projection_without_store_raises() -> None:
    from aod.application import Projection

    class SomeProjection(Projection[str]):
        pass

    uow = AsyncSpyUnitOfWork()
    with pytest.raises(DomainException, match="No ProjectionStore configured"):
        await uow.projection(SomeProjection())


async def test_async_unit_of_work_projection_with_store() -> None:
    from aod.application import Projection

    class TestProjection(Projection[str]):
        pass

    class FakeStore[TestProjection]:
        async def projection(self, p):
            return "ok"

    uow = AsyncSpyUnitOfWork(projection_store=FakeStore())
    result = await uow.projection(TestProjection())
    assert result == "ok"


async def test_async_unit_of_work_projection_with_sync_store() -> None:
    from aod.application import Projection

    class TestProjection(Projection[str]):
        pass

    class SyncFakeStore[TestProjection]:
        def projection(self, p):
            return "sync"

    uow = AsyncSpyUnitOfWork(projection_store=SyncFakeStore())
    result = await uow.projection(TestProjection())
    assert result == "sync"
