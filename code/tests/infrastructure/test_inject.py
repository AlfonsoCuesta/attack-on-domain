from __future__ import annotations

import pytest
from aod._internal.application.logger.null_logger import NullLogger
from aod._internal.application.port import Port
from aod._internal.core.infrastructure_exception import PortNotFoundError, SessionNotFoundError
from aod._internal.infrastructure.container import AdapterContainerBase
from aod._internal.infrastructure.handlers import AsyncCommandHandler
from aod._internal.infrastructure.inject import (
    extract_port_type,
    inject_adapters,
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
    weather_client: _FakePort


class TestExtractPortType:
    def test_returns_port_type(self) -> None:
        assert extract_port_type(_FakePort) is _FakePort

    def test_returns_none_for_non_port(self) -> None:
        assert extract_port_type(int) is None

    def test_returns_none_for_non_type(self) -> None:
        assert extract_port_type(42) is None


class TestInjectAdapters:
    def test_injects_special_fields(self) -> None:
        class SimpleUseCase(UseCase):
            def run(self) -> None: ...

        container = _CustomContainer(weather_client=_FakePort())
        uc = inject_adapters(container, SimpleUseCase)
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
        uc = inject_adapters(container, PortUseCase)
        assert isinstance(uc.weather_client, _FakePort)

    def test_overrides_special_field(self) -> None:
        class SimpleUseCase(UseCase):
            def run(self) -> None: ...

        container = _CustomContainer(weather_client=_FakePort())
        uc = inject_adapters(container, SimpleUseCase, logger=NullLogger())
        assert isinstance(uc.logger, NullLogger)

    def test_overrides_port_field(self) -> None:
        class PortUseCase(UseCase):
            weather_client: _FakePort

            def run(self) -> None: ...

        port = _FakePort()
        override_port = _FakePort()
        container = _CustomContainer(weather_client=port)
        uc = inject_adapters(container, PortUseCase, weather_client=override_port)
        assert isinstance(uc.weather_client, _FakePort)

    def test_raises_when_port_not_found(self) -> None:
        class PortUseCase(UseCase):
            other_port: _OtherPort

            def run(self) -> None: ...

        container = _CustomContainer(weather_client=_FakePort())
        with pytest.raises(PortNotFoundError, match="No port of type"):
            inject_adapters(container, PortUseCase)

    def test_ignores_private_fields(self) -> None:
        class PrivateUseCase(UseCase):
            _internal: int = 42

            def run(self) -> None: ...

        container = _CustomContainer(weather_client=_FakePort())
        uc = inject_adapters(container, PrivateUseCase)
        assert uc._internal == 42

    def test_ignores_fields_without_type_hints(self) -> None:
        class NoHintUseCase(UseCase):
            def run(self) -> None: ...

        container = _CustomContainer(weather_client=_FakePort())
        uc = inject_adapters(container, NoHintUseCase)
        assert uc.uow is not None

    def test_works_with_async_use_case(self) -> None:
        class AsyncPortUseCase(AsyncUseCase):
            weather_client: _FakePort

            async def run(self) -> None: ...

        port = _FakePort()
        container = _CustomContainer(weather_client=port)
        uc = inject_adapters(container, AsyncPortUseCase)
        assert isinstance(uc.weather_client, _FakePort)


class TestInjectProjection:
    def test_injects_session_and_logger(self) -> None:
        class TestProjection(ReadProjection):
            def read(self, model: ReadModel) -> str:
                return "ok"

        container = _CustomContainer(weather_client=_FakePort(), sessions={_SyncSession})
        uc = inject_adapters(container, TestProjection)
        p = uc
        assert isinstance(p.session, Session)
        assert p.logger is not None
        assert p.event_bus is not None
        assert p.cache is not None

    def test_injects_session_from_container(self) -> None:
        class TestProjection(ReadProjection):
            def read(self, model: ReadModel) -> str:
                return "ok"

        container = _CustomContainer(weather_client=_FakePort(), sessions={_SyncSession})
        uc = inject_adapters(container, TestProjection)
        p = uc
        assert isinstance(p.session, Session)

    def test_session_is_none_when_no_sessions(self) -> None:
        class TestProjection(ReadProjection):
            def read(self, model: ReadModel) -> str:
                return "ok"

        container = _CustomContainer(weather_client=_FakePort())

        with pytest.raises(SessionNotFoundError):
            inject_adapters(container, TestProjection)

    def test_overrides_session(self) -> None:
        class TestProjection(ReadProjection):
            def read(self, model: ReadModel) -> str:
                return "ok"

        override_session = _SyncSession()
        container = _CustomContainer(weather_client=_FakePort(), sessions={_SyncSession})
        uc = inject_adapters(container, TestProjection, session=override_session)
        p = uc
        assert isinstance(p.session, Session)
