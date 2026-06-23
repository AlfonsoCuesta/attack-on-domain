from __future__ import annotations

from typing import Any, cast

import pytest
from aod._internal.application.event_bus import EventBus
from aod._internal.application.handler import CommandPort
from aod._internal.application.logger import Logger
from aod._internal.application.port import Port
from aod._internal.application.use_case import UseCase
from aod._internal.core.event_emitter import Event
from aod._internal.core.infrastructure_exception import PortNotFoundError
from aod._internal.infrastructure.container import AdapterContainer
from aod._internal.infrastructure.projection import ReadProjection
from aod._internal.infrastructure.projection.models import ReadModel
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.infrastructure.unit_of_work import UnitOfWork
from aod._internal.testing.doubles.infrastructure.container import spy_adapter_container
from aod.application import Command, Query
from aod.domain import RootEntity
from aod.infrastructure import CommandHandler, QueryHandler


class User(RootEntity):
    id: int
    name: str


class GetUser(Query[User, User | None]):
    user_id: int


class CreateUser(Command[User, User]):
    name: str


class GetUserHandler(QueryHandler[GetUser]):
    def handle(self, query: GetUser) -> User | None:
        return User(id=1, name=str(query.user_id))


class CreateUserHandler(CommandHandler[CreateUser]):
    def handle(self, command: CreateUser) -> User:
        return User(id=1, name=command.name)


class _FakePort(Port):
    value: str = "default"


class _MyContainer(AdapterContainer):
    weather: _FakePort


def test_returns_instance_of_original_class() -> None:
    container = spy_adapter_container(_MyContainer(weather=_FakePort()))
    assert isinstance(container, _MyContainer)


def test_spy_bundle_provides_port_and_session_stubs() -> None:
    container = spy_adapter_container(_MyContainer(weather=_FakePort()))
    assert container.get_port_stub(Logger) is not None
    assert container.get_session_stub(Session) is not None


def test_get_session_stub() -> None:
    container = spy_adapter_container(_MyContainer(weather=_FakePort()))
    session = container.get_session_stub(Session)
    assert session is not None


def test_get_port_stub() -> None:
    container = spy_adapter_container(_MyContainer(weather=_FakePort()))
    stub = container.get_port_stub(Logger)
    assert stub is not None


def test_spy_get_port_raises_when_port_not_registered() -> None:
    container = spy_adapter_container(_MyContainer(weather=_FakePort()))
    with pytest.raises(PortNotFoundError):
        container.get_port(Logger)


def test_get_session_returns_stub_instance() -> None:
    original = _MyContainer(sessions={Session}, weather=_FakePort())
    container = spy_adapter_container(original)
    session = cast(Any, container.get_session(Session))
    session.is_dirty.returns(True)
    assert session.is_dirty() is True


def test_get_async_session_returns_stub_instance() -> None:
    original = _MyContainer(sessions={AsyncSession}, weather=_FakePort())
    container = spy_adapter_container(original)
    session = cast(Any, container.get_session(AsyncSession))
    session.is_dirty.returns(True)
    assert session.is_dirty() is True


def test_get_handler_returns_stub() -> None:
    original = _MyContainer(sessions={Session}, handlers=[GetUserHandler], weather=_FakePort())
    container = spy_adapter_container(original)
    handler = cast(Any, container.get_handler(GetUser))
    assert isinstance(handler, GetUserHandler)
    handler.handle(GetUser(user_id=1))
    assert handler.handle.called


def test_with_adapters_preserves_session_stub() -> None:
    original = _MyContainer(sessions={Session}, weather=_FakePort())
    container = spy_adapter_container(original)
    container.get_session_stub(Session).is_dirty.returns(True)
    copied = container.with_adapters(weather=_FakePort(value="new"))
    assert cast(Any, copied.get_session(Session)).is_dirty() is True
    assert copied.weather is not None
    assert copied.weather.value == "new"


def test_spy_session_commit_inside_uow_succeeds() -> None:
    container = spy_adapter_container(_MyContainer(weather=_FakePort()))
    session = container.get_session_stub(Session)
    session.is_dirty.returns(True)
    uow = UnitOfWork(sessions={session})
    uow.commit()


def test_spy_logger_records_calls() -> None:
    container = spy_adapter_container(_MyContainer(weather=_FakePort()))
    logger_stub = container.get_port_stub(Logger)
    logger_stub.info("test message")
    assert logger_stub.info.call_count == 1
    assert logger_stub.info.calls[0].args() == ("test message",)


def test_spy_event_bus_records_calls() -> None:
    class _TestEvent(Event):
        pass

    container = spy_adapter_container(_MyContainer(weather=_FakePort()))
    event_bus_stub = container.get_port_stub(EventBus)
    event_bus_stub.publish(_TestEvent())
    assert event_bus_stub.publish.call_count == 1


def test_port_overrides_are_applied() -> None:
    port = _FakePort(value="custom")
    container = spy_adapter_container(_MyContainer(weather=port))
    assert container.weather is not None
    assert container.weather.value == "custom"


def test_original_sessions_are_preserved() -> None:
    class _MySession(Session):
        def execute(self, operation: object) -> object:
            return None

        def query(self, operation: object) -> object:
            return None

        def begin(self) -> None:
            pass

        def commit(self) -> None:
            pass

        def rollback(self) -> None:
            pass

        def close(self) -> None:
            pass

        def is_dirty(self) -> bool:
            return False

    original = _MyContainer(sessions={_MySession}, weather=_FakePort())
    container = spy_adapter_container(original)
    assert _MySession in container.sessions


class _UpdateName(Command[User, None]):
    user_id: int
    name: str


class _UpdateNameUseCase(UseCase):
    update: CommandPort[_UpdateName]

    def run(self, user_id: int, name: str) -> None:
        self.update.handle(_UpdateName(user_id=user_id, name=name))


class UpdateNameHandler(CommandHandler[_UpdateName]):
    def handle(self, command: _UpdateName) -> None: ...


def test_adapt_use_case_with_returns_stubs_run_method() -> None:
    container = spy_adapter_container(
        AdapterContainer(handlers=[UpdateNameHandler], sessions={Session})
    )
    uc = container.adapt_use_case(_UpdateNameUseCase, returns=42)
    result = uc.run(user_id=1, name="Alice")
    assert result == 42


def test_adapt_use_case_without_returns_runs_normally() -> None:
    container = spy_adapter_container(
        AdapterContainer(handlers=[UpdateNameHandler], sessions={Session})
    )
    uc = container.adapt_use_case(_UpdateNameUseCase)
    result = uc.run(user_id=1, name="Alice")
    assert result is None


def test_adapt_use_case_without_returns_works_normally() -> None:
    class _PortUseCase(UseCase):
        weather: _FakePort

        def run(self) -> None: ...

    container = spy_adapter_container(_MyContainer(weather=_FakePort()))
    uc = container.adapt_use_case(_PortUseCase)
    assert isinstance(uc.weather, _FakePort)


class _TestReadProjection(ReadProjection):
    def read(self, model: ReadModel) -> str:
        return "original"


def test_adapt_projection_with_read_returns() -> None:
    container = spy_adapter_container(AdapterContainer(sessions={Session}))
    proj = container.adapt_projection(_TestReadProjection, read_returns="spied")
    result = proj.read(ReadModel())
    assert result == "spied"


def test_adapt_projection_with_write_returns() -> None:
    class _TestWriteProjection(ReadProjection):
        def read(self, model: ReadModel) -> str:
            return "read"

        def write(self, model: ReadModel) -> str:
            return "original"

    container = spy_adapter_container(AdapterContainer(sessions={Session}))
    proj = container.adapt_projection(_TestWriteProjection, write_returns="spied")
    result = proj.write(ReadModel())
    assert result == "spied"


def test_adapt_projection_without_stubs_works_normally() -> None:
    container = spy_adapter_container(AdapterContainer(sessions={Session}))
    proj = container.adapt_projection(_TestReadProjection)
    assert proj.read(ReadModel()) == "original"
