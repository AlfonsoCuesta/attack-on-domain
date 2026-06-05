from __future__ import annotations

from typing import Any, Generic, TypeVar

import pytest
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.event_emitter import Event
from aod._internal.domain.entity import RootEntity
from aod.application import Command, Query
from aod.application.event_bus.async_ import EventBus as AsyncEventBus
from aod.application.logger.async_ import Logger as AsyncLogger
from aod.application.unit_of_work.async_ import UnitOfWork as AsyncUnitOfWork
from tests.doubles import LogEntry


class AsyncSpyLogger(AsyncLogger):
    def __init__(self, **data: Any) -> None:
        object.__setattr__(self, "_entries", [])
        super().__init__(**data)

    @property
    def entries(self) -> list[LogEntry]:
        return list(self._entries)

    async def debug(self, msg: str, **context: object) -> None:
        self._entries.append(LogEntry("debug", msg, **context))

    async def info(self, msg: str, **context: object) -> None:
        self._entries.append(LogEntry("info", msg, **context))

    async def warning(self, msg: str, **context: object) -> None:
        self._entries.append(LogEntry("warning", msg, **context))

    async def error(self, msg: str, **context: object) -> None:
        self._entries.append(LogEntry("error", msg, **context))


class AsyncSpyEventBus(AsyncEventBus):
    def __init__(self, **data: Any) -> None:
        object.__setattr__(self, "_published", [])
        super().__init__(**data)

    @property
    def published(self) -> list[Event]:
        return list(self._published)

    async def publish(self, *events: Event) -> None:
        self._published.extend(events)


class AsyncSpyUnitOfWork(AsyncUnitOfWork):
    def __init__(self, **data: Any) -> None:
        object.__setattr__(self, "_committed", False)
        object.__setattr__(self, "_rolled_back", False)
        object.__setattr__(self, "_flushed", False)
        super().__init__(**data)

    @property
    def committed(self) -> bool:
        return self._committed

    @property
    def rolled_back(self) -> bool:
        return self._rolled_back

    @property
    def flushed(self) -> bool:
        return self._flushed

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        self._rolled_back = True

    async def flush(self) -> None:
        self._flushed = True


async def test_async_logger_concrete() -> None:
    log = AsyncSpyLogger()
    await log.info("hello", user_id=42)
    assert len(log.entries) == 1
    assert log.entries[0].msg == "hello"
    assert log.entries[0].context == {"user_id": 42}


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
