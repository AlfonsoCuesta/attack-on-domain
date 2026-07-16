from __future__ import annotations

import pytest
from aod._internal.application.cache.cache import Cache
from aod._internal.application.contracts import Command
from aod._internal.application.port import Port
from aod._internal.core.base_guarded import BaseGuarded
from aod._internal.core.fields.fields import Field
from aod._internal.core.infrastructure_exception import AbstractSessionTypeError
from aod._internal.domain.entity import RootEntity
from aod._internal.infrastructure.container import AdapterContainer
from aod._internal.infrastructure.container.handler_manager import HandlerManager
from aod._internal.infrastructure.container.port_manager import PortManager
from aod._internal.infrastructure.container.session_manager import SessionManager
from aod._internal.infrastructure.handlers import AsyncCommandHandler, CommandHandler
from aod._internal.infrastructure.projection import ProjectionBase, ReadProjection
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.testing.doubles.infrastructure.session import session_stub


class CustomPort(Port):
    pass


class ExtraPort(Port):
    pass


class WithPort(BaseGuarded):
    p: CustomPort
    x: int = 1


class User(RootEntity):
    id: int = Field(id=True)
    name: str


class SaveUser(Command[User, None]):
    user_id: str


StubSession = session_stub(Session)
StubAsyncSession = session_stub(AsyncSession)


class TestAsyncHandler:
    def test_async_handler_get_handler_works(self) -> None:
        class _AsyncHandler(AsyncCommandHandler[SaveUser]):
            session: StubAsyncSession

            async def handle(self, command: SaveUser) -> None:
                pass

        container = AdapterContainer(handlers=[_AsyncHandler], sessions={StubAsyncSession})
        handler = container.get_handler(SaveUser)
        assert handler.session is not None


class TestSessionCaching:
    def test_get_session_returns_cached_instance(self) -> None:
        container = AdapterContainer(sessions={StubSession})
        first = container.get_session(StubSession)
        second = container.get_session(StubSession)
        assert first is second


def test_get_all_sessions() -> None:
    container = AdapterContainer(sessions={StubSession})
    container.get_session(StubSession)
    sessions = container._session_manager.get_all_sessions()
    assert isinstance(sessions, set)
    assert len(sessions) == 1
    assert next(iter(sessions)) is container._session_manager.get_session(StubSession)


class TestPortManager:
    def test_build_index_indexes_port_fields(self) -> None:
        port = CustomPort()
        obj = WithPort(p=port)
        pm = PortManager(instance=obj)
        assert pm.ports_by_name["p"] is port


class TestInvalidSession:
    def test_abstract_session_on_projection_raises(self) -> None:
        with pytest.raises(AbstractSessionTypeError):

            class _Proj(ProjectionBase):
                session: Session


class TestProjectionInjection:
    def test_override_session_via_kwargs(self) -> None:
        class _MyProj(ProjectionBase):
            session: StubSession

        container = AdapterContainer(sessions={StubSession})
        stub = container.get_session(StubSession)
        proj = container.adapt(_MyProj)
        assert object.__getattribute__(proj, "session") is stub

    def test_extra_port_resolved_by_type(self) -> None:
        class _MyProj(ReadProjection):
            session: StubSession
            extra: ExtraPort

            def read(self, model: object) -> object:
                return {"extra": self.extra}

        extra_port = ExtraPort()
        container = AdapterContainer(
            sessions={StubSession},
            ports={ExtraPort: extra_port},
        )
        proj = container.adapt(_MyProj)
        assert object.__getattribute__(proj, "extra") is extra_port


class _CacheCmd(Command[User, None]):
    user_id: str


class _CacheH(CommandHandler[_CacheCmd]):
    session: StubSession

    def handle(self, command: _CacheCmd) -> None:
        pass


class _NullCache(Cache):
    def get(self, key: str) -> None:
        return None

    def set(self, key: str, value: object, ttl: float | None = None) -> None:
        pass

    def delete(self, key: str) -> None:
        pass


class TestHandlerManagerCaches:
    def test_non_cache_in_caches_skipped(self) -> None:
        sm = SessionManager(sessions={StubSession})
        hm = HandlerManager(
            handlers=[_CacheH],
            session_manager=sm,
            caches=["not-a-cache"],  # type: ignore
        )
        handler = hm.get_handler(_CacheCmd)
        assert handler is not None

    def test_cache_with_empty_keys_matched_by_contract(self) -> None:
        empty_cache = _NullCache(keys=[])
        sm = SessionManager(sessions={StubSession})
        hm = HandlerManager(
            handlers=[_CacheH],
            session_manager=sm,
            caches=[empty_cache],
        )
        handler = hm.get_handler(_CacheCmd)
        assert handler is not None
        assert handler._caches == []
