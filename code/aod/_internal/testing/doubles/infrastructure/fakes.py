from __future__ import annotations

from typing import Any

from aod._internal.application.port import Port
from aod._internal.infrastructure.container.handler_manager import HandlerManager
from aod._internal.infrastructure.container.port_manager import PortManager
from aod._internal.infrastructure.container.session_manager import SessionManager
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.testing.doubles.infrastructure.session import session_stub
from aod._internal.testing.doubles.stubs import port_stub


class FakeSessionManager(SessionManager):
    def __init__(
        self,
        sessions: set[type[Session] | type[AsyncSession]] | None = None,
        *,
        stub_factory: Any = None,
    ) -> None:
        self._stub_factory = stub_factory
        super().__init__(sessions)

    def _instantiate_session(
        self, session_cls: type[Session] | type[AsyncSession]
    ) -> Session | AsyncSession:
        if self._stub_factory is not None:
            return self._stub_factory(session_cls)
        return session_stub(session_cls)()


class FakeHandlerManager(HandlerManager):
    def __init__(
        self,
        handlers: list | None = None,
        session_manager: SessionManager | None = None,
        *,
        stub_factory: Any = None,
    ) -> None:
        self._stub_factory = stub_factory
        super().__init__(handlers, session_manager)

    def _instantiate_handler(
        self,
        handler: type,
        session: Session | AsyncSession | None,
    ) -> Any:
        if self._stub_factory is not None:
            return self._stub_factory(handler, session)
        return handler(session=session)


class FakePortManager(PortManager):
    def __init__(
        self,
        ports: dict[type[Port], Port] | None = None,
        instance: Any | None = None,
        extra_ports: dict[str, Port] | None = None,
        *,
        stub_factory: Any = None,
    ) -> None:
        self._stub_factory = stub_factory
        super().__init__(ports, instance, extra_ports)

    def _build_index(self, instance: Any, extra_ports: dict[str, Port] | None = None) -> None:
        super()._build_index(instance, extra_ports)
        for name in list(self.ports_by_name):
            value = self.ports_by_name[name]
            if not isinstance(value, Port):
                continue
            port_cls = type(value)
            if self._stub_factory is not None:
                self.ports_by_name[name] = self._stub_factory(name, port_cls)
            else:
                self.ports_by_name[name] = port_stub(port_cls)()


__all__ = [
    "FakeSessionManager",
    "FakeHandlerManager",
    "FakePortManager",
]
