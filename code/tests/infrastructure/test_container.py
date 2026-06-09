from __future__ import annotations

from unittest.mock import patch

import pytest
from aod._internal.application.port import Port
from aod._internal.core.infrastructure_exception import (
    DuplicateHandlerError,
    HandlerModelError,
    HandlerNotFoundError,
    InvalidPortFieldError,
    PortNotFoundError,
    SessionNotFoundError,
)
from aod._internal.infrastructure.container import AdapterContainerBase
from aod._internal.infrastructure.handlers import AsyncCommandHandler
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.infrastructure.unit_of_work import AsyncUnitOfWork, UnitOfWork
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


class _NoSessionHandler(CommandHandler[CreateUser]):
    session: None = None

    def handle(self, command: CreateUser) -> User:
        return User(id=1, name=command.name)


class _FakePort(Port):
    def __init__(self) -> None:
        super().__init__()


class _OtherPort(Port):
    pass


class _NotAPort:
    pass


class _CustomContainer(AdapterContainerBase):
    weather_client: _FakePort | None = None


class _SyncSession(Session):
    def execute(self, operation: object) -> object: ...
    def query(self, operation: object) -> object: ...
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def is_dirty(self) -> bool:
        return False


class _AsyncSession(AsyncSession):
    async def execute(self, operation: object) -> object: ...
    async def query(self, operation: object) -> object: ...
    async def begin(self) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def close(self) -> None: ...
    def is_dirty(self) -> bool:
        return False


def test_can_instantiate_with_defaults() -> None:
    container = AdapterContainerBase()
    assert container.sessions == set()
    assert container.logger is None
    assert container.event_bus is None
    assert container.cache is None
    assert container.handlers == []


def test_uow_with_sync_sessions() -> None:
    container = AdapterContainerBase(sessions={_SyncSession()})
    uow = container.get_uow()
    assert isinstance(uow, UnitOfWork)
    assert not isinstance(uow, AsyncUnitOfWork)


def test_uow_with_async_sessions() -> None:
    container = AdapterContainerBase(sessions={_AsyncSession()})
    uow = container.get_uow()
    assert isinstance(uow, AsyncUnitOfWork)


def test_uow_with_empty_sessions() -> None:
    container = AdapterContainerBase()
    uow = container.get_uow()
    assert isinstance(uow, UnitOfWork)


def test_with_adapters_returns_copy() -> None:
    container = AdapterContainerBase()
    copied = container.with_adapters(sessions={_SyncSession()})
    assert copied is not container
    assert len(copied.sessions) == 1
    assert container.sessions == set()


def test_copy_through_with_adapters() -> None:
    container = AdapterContainerBase()
    session = _SyncSession()
    copied = container.with_adapters(sessions={session})
    assert session in copied.sessions


def test_subclass_with_port_field_works() -> None:
    container = _CustomContainer(weather_client=_FakePort())
    assert isinstance(container.weather_client, _FakePort)


def test_subclass_with_port_field_default_none() -> None:
    container = _CustomContainer()
    assert container.weather_client is None


def test_subclass_non_port_field_raises_at_definition() -> None:
    with pytest.raises(InvalidPortFieldError, match="must be a Port subclass"):

        class _Bad(AdapterContainerBase):
            bad_field: int


def test_subclass_non_port_optional_raises() -> None:
    with pytest.raises(InvalidPortFieldError, match="must be a Port subclass"):

        class _Bad(AdapterContainerBase):
            bad_field: str | None = None


def test_inherited_fields_are_not_revalidated() -> None:
    class _Custom(AdapterContainerBase):
        logger: _FakePort | None = None

    assert hasattr(_Custom, "logger")


class TestGetPort:
    def test_finds_existing_port(self) -> None:
        port = _FakePort()
        container = _CustomContainer(weather_client=port)
        result = container.get_port(_FakePort)
        assert isinstance(result, _FakePort)

    def test_raises_when_port_not_found(self) -> None:
        container = _CustomContainer()
        with pytest.raises(PortNotFoundError, match="No port of type"):
            container.get_port(_OtherPort)

    def test_returns_none_field(self) -> None:
        container = _CustomContainer(weather_client=None)
        result = container.get_port(_FakePort)
        assert result is None


class TestFindHandler:
    def test_finds_handler_by_contract(self) -> None:
        container = AdapterContainerBase(handlers=[GetUserHandler])
        found = container._find_handler(GetUser)
        assert found is GetUserHandler

    def test_raises_when_no_match(self) -> None:
        container = AdapterContainerBase()
        with pytest.raises(HandlerNotFoundError, match="No handler handler registered for"):
            container._find_handler(GetUser)

    def test_ignores_handler_for_different_contract(self) -> None:
        container = AdapterContainerBase(handlers=[CreateUserHandler])
        with pytest.raises(HandlerNotFoundError, match="No handler handler registered for"):
            container._find_handler(GetUser)

    def test_matches_exact_contract_not_subclass(self) -> None:
        class _SubQuery(GetUser):
            extra: int

        container = AdapterContainerBase(handlers=[GetUserHandler])
        with pytest.raises(HandlerNotFoundError, match="No handler handler registered for"):
            container._find_handler(_SubQuery)


class TestGetSession:
    def test_finds_sync_session(self) -> None:
        session = _SyncSession()
        container = AdapterContainerBase(sessions={session})
        result = container._get_session(Session)
        assert result is session

    def test_finds_async_session(self) -> None:
        session = _AsyncSession()
        container = AdapterContainerBase(sessions={session})
        result = container._get_session(AsyncSession)
        assert result is session

    def test_raises_when_session_type_missing(self) -> None:
        container = AdapterContainerBase()
        with pytest.raises(SessionNotFoundError, match="No session of type"):
            container._get_session(Session)

    def test_returns_first_match(self) -> None:
        s1 = _SyncSession()
        s2 = _SyncSession()
        container = AdapterContainerBase(sessions={s1, s2})
        result = container._get_session(Session)
        assert result in {s1, s2}


class TestGetHandler:
    def test_returns_handler_instance(self) -> None:
        session = _SyncSession()
        container = AdapterContainerBase(
            handlers=[GetUserHandler],
            sessions={session},
        )
        handler = container.get_handler(GetUser)
        assert isinstance(handler, GetUserHandler)

    def test_passes_session_to_handler(self) -> None:
        session = _SyncSession()
        container = AdapterContainerBase(
            handlers=[GetUserHandler],
            sessions={session},
        )
        handler = container.get_handler(GetUser)
        assert isinstance(handler.session, Session)

    def test_raises_when_no_handler_found(self) -> None:
        container = AdapterContainerBase()
        with pytest.raises(HandlerNotFoundError, match="No handler handler registered for"):
            container.get_handler(GetUser)

    def test_supports_handler_without_session(self) -> None:
        container = AdapterContainerBase(handlers=[_NoSessionHandler])
        handler = container.get_handler(CreateUser)
        assert isinstance(handler, _NoSessionHandler)
        assert handler.session is None

    def test_raises_handler_model_error_when_session_field_missing(self) -> None:
        class _BadHandler(CommandHandler[CreateUser]):
            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        with patch(
            "aod._internal.infrastructure.container.get_type_hints",
            side_effect=[{"command": CreateUser}, {"command": CreateUser}, {}],
        ):
            container = AdapterContainerBase(handlers=[_BadHandler])
            with pytest.raises(HandlerModelError, match="is missing required field 'session'"):
                container.get_handler(CreateUser)

    def test_raises_session_not_found_error(self) -> None:
        container = AdapterContainerBase(handlers=[GetUserHandler])
        with pytest.raises(SessionNotFoundError, match="No session of type"):
            container.get_handler(GetUser)

    def test_duplicate_sync_handler_raises(self) -> None:
        class _HandlerA(CommandHandler[CreateUser]):
            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        class _HandlerB(CommandHandler[CreateUser]):
            def handle(self, command: CreateUser) -> User:
                return User(id=2, name=command.name)

        with pytest.raises(DuplicateHandlerError, match="Duplicate handler for"):
            AdapterContainerBase(handlers=[_HandlerA, _HandlerB])

    def test_duplicate_async_handler_raises(self) -> None:
        class _HandlerA(AsyncCommandHandler[CreateUser]):
            async def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        class _HandlerB(AsyncCommandHandler[CreateUser]):
            async def handle(self, command: CreateUser) -> User:
                return User(id=2, name=command.name)

        with pytest.raises(DuplicateHandlerError, match="Duplicate handler for"):
            AdapterContainerBase(handlers=[_HandlerA, _HandlerB])

    def test_duplicate_query_handler_raises(self) -> None:
        class _HandlerA(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return User(id=1, name=str(query.user_id))

        class _HandlerB(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return User(id=2, name=str(query.user_id))

        with pytest.raises(DuplicateHandlerError, match="Duplicate handler for"):
            AdapterContainerBase(handlers=[_HandlerA, _HandlerB])

    def test_sync_and_async_handlers_for_same_contract_raises(self) -> None:
        class _SyncHandler(CommandHandler[CreateUser]):
            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        class _AsyncHandler(AsyncCommandHandler[CreateUser]):
            async def handle(self, command: CreateUser) -> User:
                return User(id=2, name=command.name)

        with pytest.raises(DuplicateHandlerError, match="Duplicate handler for"):
            AdapterContainerBase(handlers=[_SyncHandler, _AsyncHandler])

    def test_different_contracts_do_not_raise(self) -> None:
        class _Create(CommandHandler[CreateUser]):
            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        class _Get(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return User(id=1, name=str(query.user_id))

        container = AdapterContainerBase(handlers=[_Create, _Get])
        assert len(container.handlers) == 2
