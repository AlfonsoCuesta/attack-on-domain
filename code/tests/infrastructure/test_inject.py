from __future__ import annotations

import pytest
from aod._internal.application.cache import Cache
from aod._internal.application.event_bus import EventBus
from aod._internal.application.logger import Logger
from aod._internal.application.port import Port
from aod._internal.core.fields.fields import Field
from aod._internal.core.infrastructure_exception import PortNotFoundError
from aod._internal.infrastructure.container import AdapterContainer, extract_port_type
from aod._internal.infrastructure.handlers import AsyncCommandHandler
from aod._internal.infrastructure.projection import ReadProjection
from aod._internal.infrastructure.session import AsyncSession, Session
from aod.application import Command, Query, UseCase
from aod.application.async_ import UseCase as AsyncUseCase
from aod.domain import RootEntity
from aod.infrastructure import CommandHandler, QueryHandler
from aod.testing.doubles.application import SpyCache, SpyEventBus, SpyLogger
from pydantic import BaseModel as DTO


class User(RootEntity):
    id: int = Field(id=True)
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


class _CustomContainer(AdapterContainer):
    weather_client: _FakePort


class _FullContainer(AdapterContainer):
    weather_client: _FakePort
    logger: Logger
    event_bus: EventBus
    cache: Cache


class _MultiCacheContainer(AdapterContainer):
    user_cache: Cache
    admin_cache: Cache


class TestExtractPortType:
    def test_returns_port_type(self) -> None:
        assert extract_port_type(_FakePort) is _FakePort

    def test_returns_none_for_non_port(self) -> None:
        assert extract_port_type(int) is None

    def test_returns_none_for_non_type(self) -> None:
        assert extract_port_type(42) is None


class TestInjectAdapters:
    def test_injects_port_field(self) -> None:
        class PortUseCase(UseCase):
            weather_client: _FakePort

            def run(self) -> None: ...

        port = _FakePort()
        container = _CustomContainer(weather_client=port)
        uc = container.adapt(PortUseCase)
        assert isinstance(uc.weather_client, _FakePort)

    def test_injects_special_fields(self) -> None:
        class SimpleUseCase(UseCase):
            logger: Logger
            event_bus: EventBus
            cache: Cache

            def run(self) -> None: ...

        container = _FullContainer(
            weather_client=_FakePort(),
            logger=SpyLogger(),
            event_bus=SpyEventBus(),
            cache=SpyCache(),
        )
        uc = container.adapt(SimpleUseCase)
        assert isinstance(uc.logger, SpyLogger)
        assert isinstance(uc.event_bus, SpyEventBus)
        assert isinstance(uc.cache, SpyCache)

    def test_overrides_port_field(self) -> None:
        class PortUseCase(UseCase):
            weather_client: _FakePort

            def run(self) -> None: ...

        port = _FakePort()
        override_port = _FakePort()
        container = _CustomContainer(weather_client=port)
        uc = container.adapt(PortUseCase, weather_client=override_port)
        assert isinstance(uc.weather_client, _FakePort)

    def test_raises_when_port_not_found(self) -> None:
        class PortUseCase(UseCase):
            other_port: _OtherPort

            def run(self) -> None: ...

        container = _CustomContainer(weather_client=_FakePort())
        with pytest.raises(PortNotFoundError, match="No port named"):
            container.adapt(PortUseCase)

    def test_ignores_private_fields(self) -> None:
        class PrivateUseCase(UseCase):
            _internal: int = 42

            def run(self) -> None: ...

        container = _CustomContainer(weather_client=_FakePort())
        uc = container.adapt(PrivateUseCase)
        assert uc._internal == 42

    def test_ignores_fields_without_type_hints(self) -> None:
        class NoHintUseCase(UseCase):
            def run(self) -> None: ...

        container = _CustomContainer(weather_client=_FakePort())
        uc = container.adapt(NoHintUseCase)
        assert uc.uow is not None

    def test_works_with_async_use_case(self) -> None:
        class AsyncPortUseCase(AsyncUseCase):
            weather_client: _FakePort

            async def run(self) -> None: ...

        port = _FakePort()
        container = _CustomContainer(weather_client=port)
        uc = container.adapt(AsyncPortUseCase)
        assert isinstance(uc.weather_client, _FakePort)

    def test_injects_multiple_ports_of_same_type(self) -> None:
        class _UserCache(SpyCache):
            pass

        class _AdminCache(SpyCache):
            pass

        class CacheUseCase(UseCase):
            user_cache: Cache
            admin_cache: Cache

            def run(self) -> None: ...

        user_cache = _UserCache()
        admin_cache = _AdminCache()
        container = _MultiCacheContainer(user_cache=user_cache, admin_cache=admin_cache)
        uc = container.adapt(CacheUseCase)
        assert isinstance(uc.user_cache, _UserCache)
        assert isinstance(uc.admin_cache, _AdminCache)


class TestInjectProjection:
    def test_injects_session_and_logger(self) -> None:
        class TestProjection(ReadProjection):
            session: _SyncSession
            logger: Logger

            def read(self, model: DTO) -> str:
                return "ok"

        container = _FullContainer(
            weather_client=_FakePort(),
            sessions={_SyncSession},
            logger=SpyLogger(),
            event_bus=SpyEventBus(),
            cache=SpyCache(),
        )
        p = container.adapt(TestProjection)
        assert isinstance(p.session, _SyncSession)
        assert isinstance(p.logger, SpyLogger)

    def test_injects_session_from_container(self) -> None:
        class TestProjection(ReadProjection):
            session: _SyncSession

            def read(self, model: DTO) -> str:
                return "ok"

        container = _CustomContainer(weather_client=_FakePort(), sessions={_SyncSession})
        p = container.adapt(TestProjection)
        assert isinstance(p.session, _SyncSession)

    def test_session_is_none_when_no_sessions(self) -> None:
        class TestProjection(ReadProjection):
            def read(self, model: DTO) -> str:
                return "ok"

        container = _CustomContainer(weather_client=_FakePort())
        container.adapt(TestProjection)

    def test_overrides_session(self) -> None:
        class TestProjection(ReadProjection):
            session: _SyncSession

            def read(self, model: DTO) -> str:
                return "ok"

        override_session = _SyncSession()
        container = _CustomContainer(weather_client=_FakePort(), sessions={_SyncSession})
        p = container.adapt(TestProjection, session=override_session)
        assert isinstance(p.session, _SyncSession)
