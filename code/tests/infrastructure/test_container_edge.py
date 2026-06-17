from __future__ import annotations

from aod._internal.application.contracts import Command
from aod._internal.domain.entity import RootEntity
from aod._internal.infrastructure.container import AdapterContainerBase
from aod._internal.infrastructure.handlers import AsyncCommandHandler
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.testing.doubles.infrastructure.session import session_stub


class User(RootEntity):
    id: int
    name: str


class SaveUser(Command[User, None]):
    user_id: str


StubSession = session_stub(Session)
StubAsyncSession = session_stub(AsyncSession)


class TestAsyncHandler:
    def test_async_handler_get_handler_works(self) -> None:
        class _AsyncHandler(AsyncCommandHandler[SaveUser]):
            session: AsyncSession

            async def handle(self, command: SaveUser) -> None:
                pass

        class _Container(AdapterContainerBase):
            pass

        container = _Container(handlers=[_AsyncHandler], sessions={StubAsyncSession})
        handler = container.get_handler(SaveUser)
        assert handler.session is not None


class TestSessionCaching:
    def test_get_session_returns_cached_instance(self) -> None:
        class _Container(AdapterContainerBase):
            pass

        container = _Container(sessions={StubSession})
        first = container.get_session(StubSession)
        second = container.get_session(StubSession)
        assert first is second
