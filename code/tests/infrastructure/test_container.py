from __future__ import annotations

from typing import Any

import pytest
from aod._internal.application.handler import CommandPort, QueryPort
from aod._internal.application.port import Port
from aod._internal.core.fields.fields import Field
from aod._internal.core.infrastructure_exception import (
    AbstractSessionTypeError,
    DuplicateHandlerError,
    HandlerModelError,
    HandlerNotFoundError,
    PortNotFoundError,
    SessionNotFoundError,
)
from aod._internal.infrastructure.container import AdapterContainer
from aod._internal.infrastructure.handlers import AsyncCommandHandler
from aod._internal.infrastructure.projection import ReadProjection
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.application.unit_of_work import UnitOfWork
from aod._internal.testing.doubles.infrastructure.container import spy_adapter_container
from aod.application import Command, Query, UseCase
from aod.domain import RootEntity
from aod.infrastructure import CommandHandler, QueryHandler
from pydantic import BaseModel as DTO


class User(RootEntity):
    id: int = Field(id=True)
    name: str


class GetUser(Query[User, User | None]):
    user_id: int


class CreateUser(Command[User, User]):
    name: str


class GetUserHandler(QueryHandler[GetUser]):
    session: _SyncSession

    def handle(self, query: GetUser) -> User | None:
        return User(id=1, name=str(query.user_id))


class CreateUserHandler(CommandHandler[CreateUser]):
    def handle(self, command: CreateUser) -> User:
        return User(id=1, name=command.name)


class _NoSessionHandler(CommandHandler[CreateUser]):
    def handle(self, command: CreateUser) -> User:
        return User(id=1, name=command.name)


class _FakePort(Port):
    def __init__(self) -> None:
        super().__init__()


class _OtherPort(Port):
    pass


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
    container = AdapterContainer()
    assert container.sessions == set()
    assert container.handlers == []


def test_with_adapters_returns_copy() -> None:
    container = AdapterContainer()
    copied = container.with_adapters(sessions={_SyncSession})
    assert copied is not container
    assert len(copied.sessions) == 1
    assert container.sessions == set()


def test_copy_through_with_adapters() -> None:
    container = AdapterContainer()
    copied = container.with_adapters(sessions={_SyncSession})
    assert _SyncSession in copied.sessions


def test_named_port_accessible_via_get_port() -> None:
    container = AdapterContainer(weather_client=_FakePort())
    assert isinstance(container.get_port("weather_client"), _FakePort)


class TestGetPort:
    def test_finds_existing_port(self) -> None:
        port = _FakePort()
        container = AdapterContainer(weather_client=port)
        result = container.get_port("weather_client")
        assert isinstance(result, _FakePort)

    def test_raises_when_port_not_found(self) -> None:
        container = AdapterContainer(weather_client=_FakePort())
        with pytest.raises(PortNotFoundError, match="No port named"):
            container.get_port("other_port")

    def test_finds_port_with_plain_type(self) -> None:
        port = _FakePort()
        container = AdapterContainer(client=port)
        result = container.get_port("client")
        assert result is port

    def test_get_port_from_cache(self) -> None:
        port = _FakePort()
        container = AdapterContainer(client=port)
        result = container.get_port("client")
        assert result is port


class TestFindHandler:
    def test_finds_handler_by_contract(self) -> None:
        container = AdapterContainer(handlers=[GetUserHandler])
        found = container._find_handler(GetUser)
        assert found is GetUserHandler

    def test_raises_when_no_match(self) -> None:
        container = AdapterContainer()
        with pytest.raises(HandlerNotFoundError, match="No handler handler registered for"):
            container._find_handler(GetUser)

    def test_ignores_handler_for_different_contract(self) -> None:
        container = AdapterContainer(handlers=[CreateUserHandler])
        with pytest.raises(HandlerNotFoundError, match="No handler handler registered for"):
            container._find_handler(GetUser)

    def test_matches_exact_contract_not_subclass(self) -> None:
        class _SubQuery(GetUser):
            extra: int

        container = AdapterContainer(handlers=[GetUserHandler])
        with pytest.raises(HandlerNotFoundError, match="No handler handler registered for"):
            container._find_handler(_SubQuery)


class TestGetSession:
    def test_finds_sync_session(self) -> None:
        container = AdapterContainer(sessions={_SyncSession})
        result = container.get_session(Session)
        assert isinstance(result, Session)

    def test_finds_async_session(self) -> None:
        container = AdapterContainer(sessions={_AsyncSession})
        result = container.get_session(AsyncSession)
        assert isinstance(result, AsyncSession)

    def test_raises_when_session_type_missing(self) -> None:
        container = AdapterContainer()
        with pytest.raises(SessionNotFoundError, match="No session of type"):
            container.get_session(Session)

    def test_returns_first_match(self) -> None:
        container = AdapterContainer(sessions={_SyncSession})
        result = container.get_session(Session)
        assert isinstance(result, Session)


class TestGetHandler:
    def test_returns_handler_instance(self) -> None:
        container = AdapterContainer(
            handlers=[GetUserHandler],
            sessions={_SyncSession},
        )
        handler = container.get_handler(GetUser)
        assert isinstance(handler, GetUserHandler)

    def test_passes_session_to_handler(self) -> None:
        container = AdapterContainer(
            handlers=[GetUserHandler],
            sessions={_SyncSession},
        )
        handler = container.get_handler(GetUser)
        assert isinstance(handler.session, Session)

    def test_raises_when_no_handler_found(self) -> None:
        container = AdapterContainer()
        with pytest.raises(HandlerNotFoundError, match="No handler handler registered for"):
            container.get_handler(GetUser)

    def test_supports_handler_without_session(self) -> None:
        container = AdapterContainer(handlers=[_NoSessionHandler])
        handler = container.get_handler(CreateUser)
        assert isinstance(handler, _NoSessionHandler)
        assert not hasattr(handler, "session")

    def test_raises_session_not_found_error(self) -> None:
        container = AdapterContainer(handlers=[GetUserHandler])
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
            AdapterContainer(handlers=[_HandlerA, _HandlerB])

    def test_duplicate_async_handler_raises(self) -> None:
        class _HandlerA(AsyncCommandHandler[CreateUser]):
            async def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        class _HandlerB(AsyncCommandHandler[CreateUser]):
            async def handle(self, command: CreateUser) -> User:
                return User(id=2, name=command.name)

        with pytest.raises(DuplicateHandlerError, match="Duplicate handler for"):
            AdapterContainer(handlers=[_HandlerA, _HandlerB])

    def test_duplicate_query_handler_raises(self) -> None:
        class _HandlerA(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return User(id=1, name=str(query.user_id))

        class _HandlerB(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return User(id=2, name=str(query.user_id))

        with pytest.raises(DuplicateHandlerError, match="Duplicate handler for"):
            AdapterContainer(handlers=[_HandlerA, _HandlerB])

    def test_sync_and_async_handlers_for_same_contract_raises(self) -> None:
        class _SyncHandler(CommandHandler[CreateUser]):
            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        class _AsyncHandler(AsyncCommandHandler[CreateUser]):
            async def handle(self, command: CreateUser) -> User:
                return User(id=2, name=command.name)

        with pytest.raises(DuplicateHandlerError, match="Duplicate handler for"):
            AdapterContainer(handlers=[_SyncHandler, _AsyncHandler])

    def test_different_contracts_do_not_raise(self) -> None:
        class _Create(CommandHandler[CreateUser]):
            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        class _Get(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return User(id=1, name=str(query.user_id))

        container = AdapterContainer(handlers=[_Create, _Get])
        assert len(container.handlers) == 2

    def test_contract_from_handler_raises_when_no_command_param(self) -> None:
        class _BadHandler(CommandHandler[CreateUser]):
            def handle(self) -> User:  # ty:ignore[invalid-method-override]
                return User(id=1, name="")

        with pytest.raises(HandlerModelError, match="handle"):
            AdapterContainer._contract_from_handler(_BadHandler)

    def test_get_handler_with_non_union_session_type(self) -> None:
        class _ExactSessionHandler(CommandHandler[CreateUser]):
            session: _SyncSession

            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        container = AdapterContainer(
            handlers=[_ExactSessionHandler],
            sessions={_SyncSession},
        )
        handler = container.get_handler(CreateUser)
        assert isinstance(handler, _ExactSessionHandler)
        assert isinstance(handler.session, _SyncSession)

    def test_get_handler_with_custom_named_session(self) -> None:
        class _Handler(CommandHandler[CreateUser]):
            db: _SyncSession

            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        container = AdapterContainer(
            handlers=[_Handler],
            sessions={_SyncSession},
        )
        handler = container.get_handler(CreateUser)
        assert isinstance(handler.db, _SyncSession)

    def test_get_handler_with_multiple_session_fields(self) -> None:
        class _Handler(CommandHandler[CreateUser]):
            read_db: _SyncSession
            write_db: _SyncSession

            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        container = AdapterContainer(
            handlers=[_Handler],
            sessions={_SyncSession},
        )
        handler = container.get_handler(CreateUser)
        assert isinstance(handler.read_db, _SyncSession)
        assert isinstance(handler.write_db, _SyncSession)

    def test_get_handler_rejects_abstract_session(self) -> None:
        with pytest.raises(AbstractSessionTypeError, match="uses abstract Session"):

            class _BadHandler(CommandHandler[CreateUser]):  # noqa: F841
                session: Session

                def handle(self, command: CreateUser) -> User:
                    return User(id=1, name=command.name)


class _TestAdapterPort(Port):
    pass


class _TestAdapterPortImpl(_TestAdapterPort):
    pass


class TestPortsDict:
    def test_ports_dict_resolves_by_type_in_use_case(self) -> None:
        class _UC(UseCase):
            user_client: _TestAdapterPort

            def run(self, dto: DTO) -> None: ...

        impl = _TestAdapterPortImpl()
        container = AdapterContainer(ports={_TestAdapterPort: impl})
        uc = container.adapt(_UC)
        assert isinstance(uc.user_client, _TestAdapterPortImpl)

    def test_named_port_wins_over_ports_dict(self) -> None:
        class _UC(UseCase):
            user_client: _TestAdapterPort

            def run(self, dto: DTO) -> None: ...

        typed_impl = _TestAdapterPortImpl()
        named_impl = _TestAdapterPortImpl()
        container = AdapterContainer(
            ports={_TestAdapterPort: typed_impl},
            user_client=named_impl,
        )
        uc = container.adapt(_UC)
        assert isinstance(uc.user_client, _TestAdapterPortImpl)

    def test_ports_dict_optional(self) -> None:
        class _UC(UseCase):
            my_port: _TestAdapterPort

            def run(self, dto: DTO) -> None: ...

        impl = _TestAdapterPortImpl()
        container = AdapterContainer(my_port=impl)
        uc = container.adapt(_UC)
        assert isinstance(uc.my_port, _TestAdapterPort)

    def test_base_container_with_named_ports(self) -> None:
        class _UC(UseCase):
            orders_client: _TestAdapterPort

            def run(self, dto: DTO) -> None: ...

        impl = _TestAdapterPortImpl()
        container = AdapterContainer(
            handlers=[],
            ports={_TestAdapterPort: impl},
        )
        uc = container.adapt(_UC)
        assert isinstance(uc.orders_client, _TestAdapterPortImpl)

    def test_base_container_named_port_overrides_ports_dict(self) -> None:
        class _UC(UseCase):
            primary: _TestAdapterPort
            secondary: _TestAdapterPort

            def run(self, dto: DTO) -> None: ...

        typed_impl = _TestAdapterPortImpl()
        named_impl = _TestAdapterPortImpl()
        container = AdapterContainer(
            handlers=[],
            ports={_TestAdapterPort: typed_impl},
            primary=named_impl,
        )
        uc = container.adapt(_UC)
        assert isinstance(uc.primary, _TestAdapterPortImpl)
        assert isinstance(uc.secondary, _TestAdapterPortImpl)


# ── UoW ──


# ── Sessions ──


def test_get_session_caches_instances() -> None:
    container = AdapterContainer(sessions={_SyncSession})
    first = container.get_session(Session)
    second = container.get_session(Session)
    assert first is second


def test_get_session_returns_concrete_class() -> None:
    container = AdapterContainer(sessions={_SyncSession})
    result = container.get_session(_SyncSession)
    assert isinstance(result, _SyncSession)


# ── copy / with_adapters ──


def test_copy_preserves_port_values() -> None:
    container = AdapterContainer(weather_client=_FakePort())
    copied = container.with_adapters()
    assert isinstance(copied.get_port("weather_client"), _FakePort)


# ── adapt UseCase ──


def test_adapt_use_case_injects_uow() -> None:
    class _UC(UseCase):
        def run(self) -> None: ...

    container = AdapterContainer()
    uc = container.adapt(_UC)
    assert isinstance(object.__getattribute__(uc, "_uow"), UnitOfWork)


def test_adapt_use_case_injects_handler_ports() -> None:
    class _UC(UseCase):
        create: CommandPort[CreateUser]

        def run(self, dto: DTO) -> None: ...

    container = AdapterContainer(
        handlers=[CreateUserHandler],
        sessions={_SyncSession},
    )
    uc = container.adapt(_UC)
    assert uc.create is not None


def test_adapt_use_case_injects_both_command_and_query_ports() -> None:
    class _UC(UseCase):
        create: CommandPort[CreateUser]
        get: QueryPort[GetUser]

        def run(self, dto: DTO) -> None: ...

    container = AdapterContainer(
        handlers=[CreateUserHandler, GetUserHandler],
        sessions={_SyncSession},
    )
    uc = container.adapt(_UC)
    assert uc.create is not None
    assert uc.get is not None


def test_spy_container_injects_both_command_and_query_ports() -> None:
    class _NoSessionQuery(QueryHandler[GetUser]):
        def handle(self, query: GetUser) -> User | None:
            return None

    class _NoSessionCmd(CommandHandler[CreateUser]):
        def handle(self, command: CreateUser) -> User:
            return User(id=1, name=command.name)

    class _UC(UseCase):
        create: CommandPort[CreateUser]
        get: QueryPort[GetUser]

        def run(self, dto: DTO) -> None: ...

    container = spy_adapter_container(
        AdapterContainer(
            handlers=[_NoSessionCmd, _NoSessionQuery],
        )
    )
    uc = container.adapt(_UC)
    assert uc.create is not None
    assert uc.get is not None


def test_adapt_use_case_with_overrides() -> None:
    class _UC(UseCase):
        def run(self, dto: DTO) -> None: ...

    container = AdapterContainer()
    uc = container.adapt(_UC, sessions={_SyncSession})
    assert container.sessions == set()
    assert isinstance(object.__getattribute__(uc, "_uow"), UnitOfWork)


# ── adapt Projection ──


def test_adapt_projection_injects_session() -> None:
    class _Proj(ReadProjection):
        session: _SyncSession

        def read(self, model: DTO) -> str:
            return "ok"

    container = AdapterContainer(sessions={_SyncSession})
    proj = container.adapt(_Proj)
    assert isinstance(proj.session, _SyncSession)


def test_adapt_projection_injects_port() -> None:
    class _Proj(ReadProjection):
        weather_client: _FakePort

        def read(self, model: DTO) -> str:
            return "ok"

    port = _FakePort()
    container = AdapterContainer(weather_client=port)
    proj = container.adapt(_Proj)
    assert isinstance(proj.weather_client, _FakePort)


def test_adapt_projection_without_ports_succeeds() -> None:
    class _DTO(DTO):
        pass

    class _Proj(ReadProjection):
        def read(self, model: _DTO) -> str:
            return "ok"

    container = AdapterContainer()
    proj = container.adapt(_Proj)
    assert proj.read(_DTO()) == "ok"


def test_adapt_projection_with_session_and_port() -> None:
    class _Proj(ReadProjection):
        db: _SyncSession
        weather_client: _FakePort

        def read(self, model: DTO) -> str:
            return "ok"

    port = _FakePort()
    container = AdapterContainer(sessions={_SyncSession}, weather_client=port)
    proj = container.adapt(_Proj)
    assert isinstance(proj.db, _SyncSession)
    assert isinstance(proj.weather_client, _FakePort)


def test_adapt_projection_with_multiple_session_names() -> None:
    class _Proj(ReadProjection):
        read_db: _SyncSession
        write_db: _SyncSession

        def read(self, model: DTO) -> str:
            return "ok"

    container = AdapterContainer(sessions={_SyncSession})
    proj = container.adapt(_Proj)
    assert isinstance(proj.read_db, _SyncSession)
    assert isinstance(proj.write_db, _SyncSession)


def test_adapt_projection_rejects_abstract_session() -> None:
    with pytest.raises(AbstractSessionTypeError, match="uses abstract Session"):

        class _Proj(ReadProjection):  # noqa: F841
            db: Session

            def read(self, model: DTO) -> str:
                return "ok"


def test_adapt_projection_rejects_abstract_async_session() -> None:
    with pytest.raises(AbstractSessionTypeError, match="uses abstract AsyncSession"):

        class _Proj(ReadProjection):  # noqa: F841
            db: AsyncSession

            def read(self, model: DTO) -> str:
                return "ok"


# ── Error handling ──


def _adapt_bad_type(container: Any, bad_cls: Any) -> Any:
    return container.adapt(bad_cls)


def test_adapt_raises_type_error() -> None:
    class _NotAnOperation:
        pass

    container = AdapterContainer()
    with pytest.raises(TypeError, match="Expected UseCase"):
        _adapt_bad_type(container, _NotAnOperation)
