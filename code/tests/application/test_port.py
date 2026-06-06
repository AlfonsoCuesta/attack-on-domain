from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

import pytest
from aod._internal.core.domain_exception import DomainException, MutationForbiddenException
from aod._internal.core.event_emitter import Event
from aod._internal.domain.entity import RootEntity
from aod.application import Command, EventBus, Logger, Port, ProjectionCommand, ProjectionQuery, Query, ReadModel, UnitOfWork, UseCase
from aod.testing.doubles import SpyEventBus, SpyLogger, SpyUnitOfWork


class RestClientExample(Port):
    timeout: int = 30

    @abstractmethod
    def get(self, url: str) -> str: ...

    @abstractmethod
    def post(self, url: str, data: str) -> str: ...


class RealRestClient(RestClientExample):
    calls: list[str] = []

    def get(self, url: str) -> str:
        self.calls.append(f"GET {url}")
        return f"response for {url}"

    def post(self, url: str, data: str) -> str:
        self.calls.append(f"POST {url}: {data}")
        return f"created {url}"


def test_port_abstract_cannot_instantiate() -> None:
    with pytest.raises(TypeError):
        RestClientExample()


def test_concrete_port_instantiation() -> None:
    client = RealRestClient()
    assert client.timeout == 30


def test_port_methods_are_wrapped() -> None:
    client = RealRestClient()
    result = client.get("/users")
    assert result == "response for /users"
    assert list(client.calls) == ["GET /users"]


def test_port_methods_can_mutate_fields() -> None:
    client = RealRestClient(timeout=60)
    client.post("/items", '{"name": "test"}')
    assert client.timeout == 60


def test_port_mutation_blocked_outside_methods() -> None:
    client = RealRestClient()
    with pytest.raises(MutationForbiddenException):
        client.timeout = 99


def test_port_custom_field_validation() -> None:
    client = RealRestClient(timeout=42)
    assert client.timeout == 42


def test_port_as_use_case_field() -> None:
    class ApiUseCase(UseCase):
        client: RealRestClient
        results: list[str] = []

        def run(self) -> None:
            r1 = self.client.get("/status")
            r2 = self.client.post("/data", "x")
            self.results = [r1, r2]

    uc = ApiUseCase(client=RealRestClient())
    uc.run()
    assert uc.results == ["response for /status", "created /data"]


def test_logger_abstract() -> None:
    with pytest.raises(TypeError):
        Logger()


def test_logger_concrete() -> None:
    log = SpyLogger()
    log.info("hello", user_id=42)
    assert len(log.entries) == 1
    assert log.entries[0].msg == "hello"
    assert log.entries[0].context == {"user_id": 42}


def test_logger_debug() -> None:
    log = SpyLogger()
    log.debug("debug msg", x=1)
    assert len(log.entries) == 1
    assert log.entries[0].level == "debug"
    assert log.entries[0].msg == "debug msg"
    assert log.entries[0].context == {"x": 1}


def test_logger_warning() -> None:
    log = SpyLogger()
    log.warning("warn msg", y=2)
    assert len(log.entries) == 1
    assert log.entries[0].level == "warning"
    assert log.entries[0].msg == "warn msg"
    assert log.entries[0].context == {"y": 2}


def test_event_bus_abstract() -> None:
    with pytest.raises(TypeError):
        EventBus()  # type: ignore[abstract]


def test_event_bus_publish() -> None:
    bus = SpyEventBus()
    e1 = Event()
    e2 = Event()
    bus.publish(e1, e2)
    assert len(bus.published) == 2


def test_unit_of_work_abstract() -> None:
    with pytest.raises(TypeError):
        UnitOfWork()  # type: ignore[abstract]


def test_unit_of_work_commit() -> None:
    uow = SpyUnitOfWork()
    uow.commit()
    assert uow.committed


def test_unit_of_work_rollback() -> None:
    uow = SpyUnitOfWork()
    uow.rollback()
    assert uow.rolled_back


def test_unit_of_work_flush() -> None:
    uow = SpyUnitOfWork()
    uow.flush()
    assert uow.flushed


class User(RootEntity):
    id: int
    name: str


T = TypeVar("T")


class CreateUser(Command[User, User]):
    name: str


class GetUser(Query[User, User | None]):
    user_id: int


class SpyRepo(Generic[T]):
    def __init__(self) -> None:
        self.commands: list[Command] = []
        self.queries: list[Query] = []

    def command(self, command: Command) -> object:
        self.commands.append(command)
        if isinstance(command, CreateUser):
            return User(id=1, name=command.name)
        return None

    def query(self, query: Query) -> object:
        self.queries.append(query)
        if isinstance(query, GetUser) and query.user_id == 1:
            return User(id=1, name="Alice")
        return None


class SpyUserRepo(SpyRepo[User]):
    pass


def test_unit_of_work_dispatch_command() -> None:
    repo = SpyUserRepo()
    uow = SpyUnitOfWork(repositories=[repo])
    result = uow.command(CreateUser(name="Bob"))
    assert isinstance(result, User)
    assert result.name == "Bob"
    assert len(repo.commands) == 1


def test_unit_of_work_is_dirty_after_command() -> None:
    repo = SpyUserRepo()
    uow = SpyUnitOfWork(repositories=[repo])
    assert not uow.is_dirty
    uow.command(CreateUser(name="Bob"))
    assert uow.is_dirty


def test_unit_of_work_is_dirty_false_after_query_only() -> None:
    repo = SpyUserRepo()
    uow = SpyUnitOfWork(repositories=[repo])
    uow.query(GetUser(user_id=1))
    assert not uow.is_dirty


def test_unit_of_work_dispatch_query() -> None:
    repo = SpyUserRepo()
    uow = SpyUnitOfWork(repositories=[repo])
    result = uow.query(GetUser(user_id=1))
    assert isinstance(result, User)
    assert result.name == "Alice"
    assert len(repo.queries) == 1


def test_unit_of_work_unknown_entity_raises() -> None:
    class OtherEntity(RootEntity):
        id: int

    class OtherCommand(Command[OtherEntity, None]):
        pass

    repo = SpyUserRepo()
    uow = SpyUnitOfWork(repositories=[repo])
    with pytest.raises(DomainException, match="No repository registered for entity OtherEntity"):
        uow.command(OtherCommand())


def test_unit_of_work_empty_repositories_raises() -> None:
    uow = SpyUnitOfWork()
    with pytest.raises(DomainException, match="No repository registered for entity User"):
        uow.command(CreateUser(name="X"))


def test_unit_of_work_cannot_determine_entity() -> None:
    class AmbiguousQuery(Query[User | None, User | None]):
        pass

    uow = SpyUnitOfWork(repositories=[SpyUserRepo()])
    with pytest.raises(DomainException, match="Cannot determine entity for query"):
        uow.query(AmbiguousQuery())


def test_unit_of_work_projection_without_store_raises() -> None:
    class StringResponse(ReadModel):
        value: str

    class SomeProjection(ProjectionQuery[StringResponse]):
        pass

    uow = SpyUnitOfWork()
    with pytest.raises(DomainException, match="No ProjectionStore configured"):
        uow.query(SomeProjection())


def test_unit_of_work_projection_with_store() -> None:
    class StringResponse(ReadModel):
        value: str

    class TestProjection(ProjectionQuery[StringResponse]):
        pass

    class FakeStore:
        def query(self, query: ProjectionQuery[StringResponse]) -> StringResponse:
            return StringResponse(value="ok")

        def command(self, command: ProjectionCommand[StringResponse]) -> StringResponse:
            return StringResponse(value="")

    uow = SpyUnitOfWork(projection_store=FakeStore())
    result: StringResponse = uow.query(TestProjection())  # type: ignore
    assert result.value == "ok"


def test_unit_of_work_save_without_store_raises() -> None:
    class SomeCommand(ProjectionCommand[None]):
        pass

    uow = SpyUnitOfWork()
    with pytest.raises(DomainException, match="No ProjectionStore configured"):
        uow.command(SomeCommand())


def test_unit_of_work_save_with_store() -> None:
    saved: list[ProjectionCommand] = []

    class SaveSomething(ProjectionCommand[None]):
        value: str

    class FakeStore:
        def query(self, query: ProjectionQuery[None]) -> None:
            return None

        def command(self, command: ProjectionCommand[None]) -> None:
            saved.append(command)
            return None

    uow = SpyUnitOfWork(projection_store=FakeStore())
    uow.command(SaveSomething(value="saved-value"))
    assert len(saved) == 1
    assert saved[0].value == "saved-value"
