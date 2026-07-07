from __future__ import annotations

from typing import Any, TypeVar, cast

from aod._internal.application.port import Port
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.infrastructure.container import AdapterContainer
from aod._internal.infrastructure.projection import ProjectionBase
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.testing.doubles.infrastructure.fakes import (
    FakeHandlerManager,
    FakePortManager,
    FakeSessionManager,
)
from aod._internal.testing.doubles.infrastructure.session import session_stub
from aod._internal.testing.doubles.stubs import _make_callable_stub, port_stub

T = TypeVar("T", bound=AdapterContainer)

_UNSET = object()


def spy_adapter_container(container: T) -> T:
    spy_cls = _create_spy_adapter(type(container))
    kwargs = {f: getattr(container, f) for f in container.__model_fields__}
    return spy_cls(**kwargs)


def _create_spy_adapter(container_cls: type[T]) -> type[T]:
    def get_port_stub(self: Any, name: str) -> Any:
        if name not in self._port_stubs:
            self._port_stubs[name] = self._port_manager.ports_by_name[name]
        return self._port_stubs[name]

    def get_session_stub(self: Any, session_cls: type[Session] | type[AsyncSession]) -> Any:
        if session_cls not in self._session_stubs:
            self._session_stubs[session_cls] = session_stub(session_cls)()
        return self._session_stubs[session_cls]

    def make_session_manager(self: Any) -> FakeSessionManager:
        return FakeSessionManager(
            self.sessions, stub_factory=lambda cls: self.get_session_stub(cls)
        )

    def make_handler_manager(self: Any, sm: Any) -> FakeHandlerManager:
        return FakeHandlerManager(
            self.handlers, sm, stub_factory=lambda h, s: self.get_handler_stub(h)
        )

    def make_port_manager(self: Any, extra_ports: dict[str, Port]) -> FakePortManager:
        return FakePortManager(self.ports, self, extra_ports)

    def get_handler_stub(self: Any, handler: type[Port]) -> Any:
        if handler not in self._handler_stubs:
            self._handler_stubs[handler] = port_stub(handler)()
        return self._handler_stubs[handler]

    def _apply_stub(stub: Any, *, returns: Any = _UNSET, raises: Any = _UNSET) -> None:
        if raises is not _UNSET:
            stub.side_effect = raises
        elif returns is not _UNSET:
            stub.return_value = returns

    def stub_use_case(
        self: Any,
        use_case_cls: type[UseCase | AsyncUseCase],
        *,
        returns: Any = _UNSET,
        raises: Any = _UNSET,
    ) -> None:
        self._use_case_stubs[use_case_cls] = dict(returns=returns, raises=raises)

    def stub_projection(
        self: Any,
        projection_cls: type[ProjectionBase],
        *,
        read_returns: Any = _UNSET,
        read_raises: Any = _UNSET,
        write_returns: Any = _UNSET,
        write_raises: Any = _UNSET,
    ) -> None:
        self._projection_stubs[projection_cls] = dict(
            read_returns=read_returns,
            read_raises=read_raises,
            write_returns=write_returns,
            write_raises=write_raises,
        )

    def _adapt_use_case_spy(
        self: Any,
        use_case_cls: type[UseCase | AsyncUseCase],
        **kwargs: Any,
    ) -> Any:
        instance = container_cls._adapt_use_case(self, use_case_cls, **kwargs)
        cfg = self._use_case_stubs.get(use_case_cls, {})
        if cfg:
            stub = _make_callable_stub(instance.run)
            _apply_stub(stub, **cfg)
            object.__setattr__(instance, "run", stub)
        return instance

    def _adapt_projection_spy(
        self: Any,
        projection_cls: type[ProjectionBase],
        **kwargs: Any,
    ) -> Any:
        instance = container_cls._adapt_projection(self, projection_cls, **kwargs)
        cfg = self._projection_stubs.get(projection_cls, {})
        if not cfg:
            return instance
        read_returns = cfg.get("read_returns", _UNSET)
        read_raises = cfg.get("read_raises", _UNSET)
        if (read_returns is not _UNSET or read_raises is not _UNSET) and getattr(
            instance, "read", None
        ):
            stub = _make_callable_stub(instance.read)
            _apply_stub(stub, returns=read_returns, raises=read_raises)
            object.__setattr__(instance, "read", stub)
        write_returns = cfg.get("write_returns", _UNSET)
        write_raises = cfg.get("write_raises", _UNSET)
        if (write_returns is not _UNSET or write_raises is not _UNSET) and getattr(
            instance, "write", None
        ):
            stub = _make_callable_stub(instance.write)
            _apply_stub(stub, returns=write_returns, raises=write_raises)
            object.__setattr__(instance, "write", stub)
        return instance

    def adapt(
        self: Any,
        operation_cls: type[UseCase | AsyncUseCase | ProjectionBase],
        **kwargs: Any,
    ) -> Any:
        if issubclass(operation_cls, (UseCase, AsyncUseCase)):
            return self._adapt_use_case_spy(operation_cls, **kwargs)
        if issubclass(operation_cls, ProjectionBase):
            return self._adapt_projection_spy(operation_cls, **kwargs)
        raise TypeError(
            f"Expected UseCase, AsyncUseCase, or ProjectionBase subclass, got {operation_cls.__name__}"
        )

    spy_cls = cast(
        type[T],
        type(
            f"Spy{container_cls.__name__}",
            (container_cls,),
            {
                "_port_stubs": {},
                "_session_stubs": {},
                "_handler_stubs": {},
                "_use_case_stubs": {},
                "_projection_stubs": {},
                "_make_session_manager": make_session_manager,
                "_make_handler_manager": make_handler_manager,
                "_make_port_manager": make_port_manager,
                "get_port_stub": get_port_stub,
                "get_session_stub": get_session_stub,
                "get_handler_stub": get_handler_stub,
                "stub_use_case": stub_use_case,
                "stub_projection": stub_projection,
                "_adapt_use_case_spy": _adapt_use_case_spy,
                "_adapt_projection_spy": _adapt_projection_spy,
                "adapt": adapt,
            },
        ),
    )

    return spy_cls
