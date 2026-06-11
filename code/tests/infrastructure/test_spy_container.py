from __future__ import annotations

from aod._internal.application.port import Port
from aod._internal.infrastructure.container import AdapterContainerBase
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.testing.doubles.application.cache import AsyncSpyCache, SpyCache
from aod._internal.testing.doubles.application.event_bus import AsyncSpyEventBus, SpyEventBus
from aod._internal.testing.doubles.application.logger import AsyncSpyLogger, SpyLogger
from aod._internal.testing.doubles.infrastructure.container import spy_adapter_container
from aod._internal.testing.doubles.infrastructure.session import SpyAsyncSession, SpySession
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


class _SpyGetUserHandler(QueryHandler[GetUser]):
    def handle(self, query: GetUser) -> User | None:
        return User(id=99, name="spy")


class _FakePort(Port):
    value: str = "default"


class _MyContainer(AdapterContainerBase):
    weather: _FakePort | None = None


class _InMemorySession(Session):
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


def test_returns_instance_of_original_class() -> None:
    container = spy_adapter_container(_MyContainer())
    assert isinstance(container, _MyContainer)


def test_spy_bundle_has_spy_types() -> None:
    container = spy_adapter_container(_MyContainer())
    spy = container.spy_bundle
    assert isinstance(spy.sync_session, SpySession)
    assert isinstance(spy.async_session, SpyAsyncSession)
    assert isinstance(spy.logger, SpyLogger)
    assert isinstance(spy.async_logger, AsyncSpyLogger)
    assert isinstance(spy.event_bus, SpyEventBus)
    assert isinstance(spy.async_event_bus, AsyncSpyEventBus)
    assert isinstance(spy.cache, SpyCache)
    assert isinstance(spy.async_cache, AsyncSpyCache)


def test_get_session_returns_spy_instance() -> None:
    original = _MyContainer(sessions={Session})
    container = spy_adapter_container(original)
    session = container.get_session(Session)
    assert session is container.spy_bundle.sync_session


def test_get_async_session_returns_spy_instance() -> None:
    original = _MyContainer(sessions={AsyncSession})
    container = spy_adapter_container(original)
    session = container.get_session(AsyncSession)
    assert session is container.spy_bundle.async_session


def test_handler_receives_spy_session() -> None:
    original = _MyContainer(sessions={Session}, handlers=[GetUserHandler])
    container = spy_adapter_container(original)
    handler = container.get_handler(GetUser)
    assert isinstance(handler.session, SpySession)


def test_double_handler_is_used() -> None:
    original = _MyContainer(sessions={Session}, handlers=[GetUserHandler])
    container = spy_adapter_container(
        original,
        double_handlers={GetUser: _SpyGetUserHandler},
    )
    handler = container.get_handler(GetUser)
    result = handler.handle(GetUser(user_id=1))
    assert result is not None
    assert result.id == 99
    assert result.name == "spy"


def test_double_session_is_used() -> None:
    in_memory = _InMemorySession()
    original = _MyContainer(sessions={Session}, handlers=[GetUserHandler])
    container = spy_adapter_container(
        original,
        double_sessions={Session: in_memory},
    )
    handler = container.get_handler(GetUser)
    assert isinstance(handler.session, _InMemorySession)


def test_with_adapters_preserves_spy_session() -> None:
    original = _MyContainer(sessions={Session})
    container = spy_adapter_container(original)
    copied = container.with_adapters(weather=_FakePort(value="new"))
    assert copied.get_session(Session) is container.spy_bundle.sync_session
    assert copied.weather.value == "new"


def test_spy_session_tracks_commits_inside_uow() -> None:
    from aod._internal.infrastructure.unit_of_work import UnitOfWork

    container = spy_adapter_container(_MyContainer())
    spy = container.spy_bundle
    object.__setattr__(spy.sync_session, "_dirty", True)
    uow = UnitOfWork(sessions={spy.sync_session})
    uow.commit()
    assert len(spy.sync_session.commit_calls) == 1


def test_spy_logger_records_entries() -> None:
    container = spy_adapter_container(_MyContainer())
    container.spy_bundle.logger.info("test message")
    assert len(container.spy_bundle.logger.entries) == 1
    assert container.spy_bundle.logger.entries[0].msg == "test message"
    assert container.spy_bundle.logger.entries[0].level == "info"


def test_spy_event_bus_records_published_events() -> None:
    from aod._internal.core.event_emitter import Event

    class _TestEvent(Event):
        pass

    container = spy_adapter_container(_MyContainer())
    container.spy_bundle.event_bus.publish(_TestEvent())
    assert len(container.spy_bundle.event_bus.published) == 1


def test_port_overrides_are_applied() -> None:
    port = _FakePort(value="custom")
    container = spy_adapter_container(_MyContainer(), weather=port)
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

    original = _MyContainer(sessions={_MySession})
    container = spy_adapter_container(original)
    assert _MySession in container.sessions
