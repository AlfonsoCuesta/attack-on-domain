from __future__ import annotations

from unittest.mock import patch

import pytest
from aod._internal.application.logger.null_logger import NullLogger
from aod._internal.application.port import Port
from aod._internal.core.infrastructure_exception import (
    HandlerNotFoundError,
    PortNotFoundError,
    SessionNotFoundError,
)
from aod._internal.infrastructure.container import AdapterContainerBase
from aod._internal.infrastructure.handlers import AsyncCommandHandler
from aod._internal.infrastructure.inject import (
    _extract_handler_contract,
    _extract_port_type,
    inject_adapters,
    inject_projection,
)
from aod._internal.infrastructure.projection import ReadModel, ReadProjection
from aod._internal.infrastructure.session import AsyncSession, Session
from aod.application import Command, Query, UseCase
from aod.application.async_ import UseCase as AsyncUseCase
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


class AsyncCreateUserHandler(AsyncCommandHandler[CreateUser]):
    async def handle(self, command: CreateUser) -> User:
        return User(id=1, name=command.name)


class _FakePort(Port):
    pass


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


class _CustomContainer(AdapterContainerBase):
    weather_client: _FakePort | None = None


class TestExtractPortType:
    def test_returns_port_type(self) -> None:
        assert _extract_port_type(_FakePort) is _FakePort

    def test_returns_none_for_non_port(self) -> None:
        assert _extract_port_type(int) is None

    def test_returns_none_for_non_type(self) -> None:
        assert _extract_port_type(42) is None


class TestExtractHandlerContract:
    def test_returns_contract_for_command_handler(self) -> None:
        assert _extract_handler_contract(CreateUserHandler) is CreateUser

    def test_returns_contract_for_query_handler(self) -> None:
        assert _extract_handler_contract(GetUserHandler) is GetUser

    def test_returns_contract_for_async_handler(self) -> None:
        assert _extract_handler_contract(AsyncCreateUserHandler) is CreateUser

    def test_returns_none_for_non_handler(self) -> None:
        assert _extract_handler_contract(int) is None

    def test_returns_none_for_non_type(self) -> None:
        assert _extract_handler_contract(42) is None

    def test_returns_none_for_handler_without_generic(self) -> None:
        class _Plain(CommandHandler):
            def handle(self, command: object) -> object: ...

        assert _extract_handler_contract(_Plain) is None


class TestInjectAdapters:
    def test_injects_special_fields(self) -> None:
        class SimpleUseCase(UseCase):
            def run(self) -> None: ...

        container = _CustomContainer()
        partial = inject_adapters(container, SimpleUseCase)
        uc = partial()
        assert uc.uow is not None
        assert uc.logger is not None
        assert uc.event_bus is not None
        assert uc.cache is not None

    def test_injects_port_field(self) -> None:
        class PortUseCase(UseCase):
            weather_client: _FakePort

            def run(self) -> None: ...

        port = _FakePort()
        container = _CustomContainer(weather_client=port)
        partial = inject_adapters(container, PortUseCase)
        uc = partial()
        assert isinstance(uc.weather_client, _FakePort)

    def test_injects_handler_field(self) -> None:
        class HandlerUseCase(UseCase):
            create_user: CreateUserHandler

            def run(self) -> None: ...

        session = _SyncSession()
        container = _CustomContainer(
            handlers=[CreateUserHandler],
            sessions={session},
        )
        partial = inject_adapters(container, HandlerUseCase)
        uc = partial()
        assert isinstance(uc.create_user, CreateUserHandler)
        assert isinstance(uc.create_user.session, Session)

    def test_injects_async_handler_field(self) -> None:
        class AsyncHandlerUseCase(AsyncUseCase):
            create_user: AsyncCreateUserHandler

            async def run(self) -> None: ...

        session = _AsyncSession()
        container = _CustomContainer(
            handlers=[AsyncCreateUserHandler],
            sessions={session},
        )
        partial = inject_adapters(container, AsyncHandlerUseCase)
        uc = partial()
        assert isinstance(uc.create_user, AsyncCreateUserHandler)
        assert isinstance(uc.create_user.session, AsyncSession)

    def test_injects_multiple_fields(self) -> None:
        class MultiUseCase(UseCase):
            weather_client: _FakePort
            create_user: CreateUserHandler

            def run(self) -> None: ...

        port = _FakePort()
        session = _SyncSession()
        container = _CustomContainer(
            weather_client=port,
            handlers=[CreateUserHandler],
            sessions={session},
        )
        partial = inject_adapters(container, MultiUseCase)
        uc = partial()
        assert isinstance(uc.weather_client, _FakePort)
        assert isinstance(uc.create_user, CreateUserHandler)

    def test_overrides_special_field(self) -> None:
        class SimpleUseCase(UseCase):
            def run(self) -> None: ...

        container = _CustomContainer()
        partial = inject_adapters(container, SimpleUseCase, logger=NullLogger())
        uc = partial()
        assert isinstance(uc.logger, NullLogger)

    def test_overrides_port_field(self) -> None:
        class PortUseCase(UseCase):
            weather_client: _FakePort

            def run(self) -> None: ...

        port = _FakePort()
        override_port = _FakePort()
        container = _CustomContainer(weather_client=port)
        partial = inject_adapters(container, PortUseCase, weather_client=override_port)
        uc = partial()
        assert isinstance(uc.weather_client, _FakePort)

    def test_overrides_handler_field(self) -> None:
        class HandlerUseCase(UseCase):
            create_user: CreateUserHandler

            def run(self) -> None: ...

        session = _SyncSession()
        container = _CustomContainer(
            handlers=[CreateUserHandler],
            sessions={session},
        )
        override_handler = CreateUserHandler(session=session)
        partial = inject_adapters(container, HandlerUseCase, create_user=override_handler)
        uc = partial()
        assert isinstance(uc.create_user, CreateUserHandler)
        assert isinstance(uc.create_user.session, Session)

    def test_raises_when_port_not_found(self) -> None:
        class PortUseCase(UseCase):
            other_port: _OtherPort

            def run(self) -> None: ...

        container = _CustomContainer()
        with pytest.raises(PortNotFoundError, match="No port of type"):
            inject_adapters(container, PortUseCase)

    def test_raises_when_handler_not_found(self) -> None:
        class HandlerUseCase(UseCase):
            create_user: CreateUserHandler

            def run(self) -> None: ...

        container = _CustomContainer()
        with pytest.raises(HandlerNotFoundError, match="No handler handler registered for"):
            inject_adapters(container, HandlerUseCase)

    def test_raises_when_handler_session_not_found(self) -> None:
        class HandlerUseCase(UseCase):
            create_user: CreateUserHandler

            def run(self) -> None: ...

        container = _CustomContainer(handlers=[CreateUserHandler])
        with pytest.raises(SessionNotFoundError, match="No session of type"):
            inject_adapters(container, HandlerUseCase)

    def test_ignores_private_fields(self) -> None:
        class PrivateUseCase(UseCase):
            _internal: int = 42

            def run(self) -> None: ...

        container = _CustomContainer()
        partial = inject_adapters(container, PrivateUseCase)
        uc = partial()
        assert uc._internal == 42

    def test_ignores_fields_without_type_hints(self) -> None:
        class NoHintUseCase(UseCase):
            def run(self) -> None: ...

        container = _CustomContainer()
        partial = inject_adapters(container, NoHintUseCase)
        uc = partial()
        assert uc.uow is not None

    def test_ignores_non_port_non_handler_fields(self) -> None:
        class OtherFieldUseCase(UseCase):
            some_value: str = "default"

            def run(self) -> None: ...

        container = _CustomContainer()
        partial = inject_adapters(container, OtherFieldUseCase)
        uc = partial()
        assert uc.some_value == "default"

    def test_skips_field_without_type_hint(self) -> None:
        class SimpleUseCase(UseCase):
            def run(self) -> None: ...

        container = _CustomContainer()
        with patch(
            "aod._internal.infrastructure.inject.get_type_hints",
            return_value={"nonexistent": None},
        ):
            partial = inject_adapters(container, SimpleUseCase)
        uc = partial()
        assert uc.uow is not None

    def test_works_with_async_use_case(self) -> None:
        class AsyncPortUseCase(AsyncUseCase):
            weather_client: _FakePort

            async def run(self) -> None: ...

        port = _FakePort()
        container = _CustomContainer(weather_client=port)
        partial = inject_adapters(container, AsyncPortUseCase)
        uc = partial()
        assert isinstance(uc.weather_client, _FakePort)

    def test_works_with_async_use_case_handler(self) -> None:
        class AsyncHandlerUseCase(AsyncUseCase):
            create_user: AsyncCreateUserHandler

            async def run(self) -> None: ...

        session = _AsyncSession()
        container = _CustomContainer(
            handlers=[AsyncCreateUserHandler],
            sessions={session},
        )
        partial = inject_adapters(container, AsyncHandlerUseCase)
        uc = partial()
        assert isinstance(uc.create_user, AsyncCreateUserHandler)
        assert isinstance(uc.create_user.session, AsyncSession)

    def test_raises_on_async_handler_without_session(self) -> None:
        class AsyncHandlerUseCase(AsyncUseCase):
            create_user: AsyncCreateUserHandler

            async def run(self) -> None: ...

        container = _CustomContainer(handlers=[AsyncCreateUserHandler])
        with pytest.raises(SessionNotFoundError, match="No session of type"):
            inject_adapters(container, AsyncHandlerUseCase)


class TestInjectProjection:
    def test_injects_session_and_logger(self) -> None:
        class TestProjection(ReadProjection):
            def read(self, model: ReadModel) -> str:
                return "ok"

        session = _SyncSession()
        container = _CustomContainer(sessions={session})
        partial = inject_projection(container, TestProjection)
        p = partial()
        assert isinstance(p.session, Session)
        assert p.logger is not None
        assert p.event_bus is not None
        assert p.cache is not None

    def test_injects_session_from_container(self) -> None:
        class TestProjection(ReadProjection):
            def read(self, model: ReadModel) -> str:
                return "ok"

        session = _SyncSession()
        container = _CustomContainer(sessions={session})
        partial = inject_projection(container, TestProjection)
        p = partial()
        assert isinstance(p.session, Session)

    def test_session_is_none_when_no_sessions(self) -> None:
        class TestProjection(ReadProjection):
            def read(self, model: ReadModel) -> str:
                return "ok"

        container = _CustomContainer()
        partial = inject_projection(container, TestProjection)
        p = partial()
        assert p.session is None

    def test_overrides_session(self) -> None:
        class TestProjection(ReadProjection):
            def read(self, model: ReadModel) -> str:
                return "ok"

        session = _SyncSession()
        override_session = _SyncSession()
        container = _CustomContainer(sessions={session})
        partial = inject_projection(container, TestProjection, session=override_session)
        p = partial()
        assert isinstance(p.session, Session)