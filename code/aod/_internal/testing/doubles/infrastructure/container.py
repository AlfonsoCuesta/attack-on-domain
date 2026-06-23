from __future__ import annotations

from typing import Any, TypeVar, cast

from aod._internal.application.port import Port
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.infrastructure.container import AdapterContainer
from aod._internal.infrastructure.projection import ProjectionBase
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.testing.doubles.infrastructure.session import session_stub
from aod._internal.testing.doubles.stubs import _make_callable_stub, port_stub

T = TypeVar("T", bound=AdapterContainer)

_UNSET = object()


def spy_adapter_container(container: T) -> T:
    """Create a spy version of an AdapterContainer.

    Sessions are replaced by stubs. Configure stubs via
    ``get_port_stub`` and ``get_session_stub``::

        container = spy_adapter_container(MyContainer())
        container.get_session_stub(Session).is_dirty.returns(True)
        container.get_port_stub(Logger).info.returns(None)
        handler = container.get_handler(GetUser)
        handler.handle(GetUser(user_id=1))

    ``adapt_projection`` accepts extra keyword arguments for configuring stub
    return values::

        proj = container.adapt_projection(MyProjection, read_returns=12, write_returns=11)
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

    def instantiate_handler(self: Any, handler: type[Port], _: Any) -> Any:
        return self.get_handler_stub(handler)

    def get_handler_stub(self: Any, handler: type[Port]) -> Any:
        if handler not in self._handler_stubs:
            self._handler_stubs[handler] = port_stub(handler)()
        stub = self._handler_stubs[handler]
        return stub

    def adapt_use_case(
        self: Any,
        use_case_cls: type[UseCase | AsyncUseCase],
        *,
        returns: Any = _UNSET,
        **kwargs: Any,
    ) -> Any:
        instance = container_cls.adapt_use_case(self, use_case_cls, **kwargs)
        if returns is not _UNSET:
            stub = _make_callable_stub(instance.run)
            stub.returns(returns)
            object.__setattr__(instance, "run", stub)
        return instance

    original_adapt_projection = container_cls.adapt_projection

    def adapt_projection(
        self: Any,
        projection_cls: type[ProjectionBase],
        *,
        read_returns: Any = _UNSET,
        write_returns: Any = _UNSET,
        **kwargs: Any,
    ) -> Any:
        proj = original_adapt_projection(self, projection_cls, **kwargs)
        if read_returns is not _UNSET and getattr(proj, "read"):
            stub = _make_callable_stub(proj.read)
            stub.returns(read_returns)
            object.__setattr__(proj, "read", stub)

        if write_returns is not _UNSET and getattr(proj, "write"):
            stub = _make_callable_stub(proj.write)
            stub.returns(write_returns)
            object.__setattr__(proj, "write", stub)

        return proj

    spy_cls = cast(
        type[T],
        type(
            f"Spy{container_cls.__name__}",
            (container_cls,),
            {
                "_port_stubs": {},
                "_session_stubs": {},
                "_handler_stubs": {},
                "_instantiate_session": instantiate_session,
                "_instantiate_handler": instantiate_handler,
                "_get_port_instance": get_port_instance,
                "get_port_stub": get_port_stub,
                "get_session_stub": get_session_stub,
                "get_handler_stub": get_handler_stub,
                "adapt_use_case": adapt_use_case,
                "adapt_projection": adapt_projection,
            },
        ),
    )

    return spy_cls
