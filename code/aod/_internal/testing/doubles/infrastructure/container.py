from __future__ import annotations

from typing import Any, TypeVar, cast

from aod._internal.application.port import Port
from aod._internal.infrastructure.container import AdapterContainer
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.testing.doubles.infrastructure.session import session_stub
from aod._internal.testing.doubles.stubs import port_stub

T = TypeVar("T", bound=AdapterContainer)


def spy_adapter_container(container: T) -> T:
    """Create a spy version of an AdapterContainer.

    Sessions are replaced by stubs. Configure stubs via
    ``get_port_stub`` and ``get_session_stub``::

        container = spy_adapter_container(MyContainer())
        container.get_session_stub(Session).is_dirty.returns(True)
        container.get_port_stub(Logger).info.returns(None)
        handler = container.get_handler(GetUser)
        handler.handle(GetUser(user_id=1))
    """
    spy_cls = _create_spy_adapter(type(container))
    kwargs = {f: getattr(container, f) for f in container.__model_fields__}
    return spy_cls(**kwargs)


def _create_spy_adapter(container_cls: type[T]) -> type[T]:
    def get_port_stub(self: Any, port_cls: type[Port]) -> Any:
        if port_cls not in self._port_stubs:
            self._port_stubs[port_cls] = port_stub(port_cls)()
        return self._port_stubs[port_cls]

    def get_session_stub(self: Any, session_cls: type[Session] | type[AsyncSession]) -> Any:
        if session_cls not in self._session_stubs:
            self._session_stubs[session_cls] = session_stub(session_cls)()
        return self._session_stubs[session_cls]

    def instantiate_session(
        self: Any, session_cls: type[Session] | type[AsyncSession]
    ) -> Session | AsyncSession:
        return self.get_session_stub(session_cls)

    def get_port_instance(self: Any, port: type[Port]) -> Port | None:
        for tp in self._ports_by_type:
            if isinstance(tp, type) and issubclass(tp, port):
                return self.get_port_stub(port)
        return None

    spy_cls = cast(
        type[T],
        type(
            f"Spy{container_cls.__name__}",
            (container_cls,),
            {
                "_port_stubs": {},
                "_session_stubs": {},
                "_instantiate_session": instantiate_session,
                "_get_port_instance": get_port_instance,
                "get_port_stub": get_port_stub,
                "get_session_stub": get_session_stub,
            },
        ),
    )

    return spy_cls
