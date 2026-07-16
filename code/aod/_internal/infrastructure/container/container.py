from __future__ import annotations

from typing import Any, Self, cast

from aod._internal.application.port import Port
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.infrastructure.container.handler_manager import HandlerManager
from aod._internal.infrastructure.container.port_manager import PortManager
from aod._internal.infrastructure.container.session_manager import SessionManager
from aod._internal.infrastructure.container.types import (
    TOperation,
    TProjection,
    TUseCase,
    _is_session_annotation,
    _validate_concrete_session,
)
from aod._internal.infrastructure.projection import ProjectionBase
from aod._internal.infrastructure.session import AsyncSession, Session


class AdapterContainer(BaseBehaviour):
    sessions: set[type[Session] | type[AsyncSession]] = Field(default_factory=set)
    handlers: list = Field(default_factory=list)
    ports: dict[type[Port], Port] = Field(default_factory=dict)
    caches: list = Field(default_factory=list)
    _session_manager: SessionManager = PrivateField()
    _handler_manager: HandlerManager = PrivateField()
    _port_manager: PortManager = PrivateField()

    def __init__(self, **kwargs: Any) -> None:
        known = set(self.__class__.__model_fields__)
        pydantic_kwargs = {k: v for k, v in kwargs.items() if k in known}
        extra_ports = {k: v for k, v in kwargs.items() if k not in known and isinstance(v, Port)}

        super().__init__(**pydantic_kwargs)

        sm = self._make_session_manager()
        hm = self._make_handler_manager(sm)
        pm = self._make_port_manager(extra_ports)

        object.__setattr__(self, "_session_manager", sm)
        object.__setattr__(self, "_handler_manager", hm)
        object.__setattr__(self, "_port_manager", pm)

    def _make_session_manager(self) -> SessionManager:
        return SessionManager(self.sessions)

    def _make_handler_manager(self, sm: SessionManager) -> HandlerManager:
        return HandlerManager(self.handlers, sm, caches=self.caches)

    def _make_port_manager(self, extra_ports: dict[str, Port]) -> PortManager:
        return PortManager(self.ports, self, extra_ports)

    def copy(self, **overrides: Any) -> Self:
        current = {}
        for k in self.__model_fields__:
            current[k] = getattr(self, k)
        for name, value in self._port_manager.ports_by_name.items():
            current[name] = value
        current.update(overrides)
        return self.__class__(**current)

    def with_adapters(self, **overrides: Any) -> Self:
        return self.copy(**overrides)

    @staticmethod
    def _contract_from_handler(h_cls: Any) -> Any:
        return HandlerManager.contract_from_handler(h_cls)

    def _find_handler(self, contract: Any) -> Any:
        return self._handler_manager.find_handler(contract)

    def get_port(self, name: str) -> Port:
        return self._port_manager.get_port(name)

    def get_session(
        self, session_cls: type[Session] | type[AsyncSession]
    ) -> Session | AsyncSession:
        return self._session_manager.get_session(session_cls)

    def get_handler(self, contract: Any) -> Any:
        return self._handler_manager.get_handler(contract)

    def adapt(
        self,
        operation_cls: type[TOperation],
        **overrides: Any,
    ) -> TOperation:
        if issubclass(operation_cls, (UseCase, AsyncUseCase)):
            return cast(TOperation, self._adapt_use_case(operation_cls, **overrides))
        if issubclass(operation_cls, ProjectionBase):
            return cast(TOperation, self._adapt_projection(operation_cls, **overrides))
        raise TypeError(
            f"Expected UseCase, AsyncUseCase, or ProjectionBase subclass, got {operation_cls.__name__}"
        )

    def _adapt_use_case(self, use_case_cls: type[TUseCase], **overrides: Any) -> TUseCase:
        container = self.with_adapters(**overrides) if overrides else self

        kwargs: dict[str, Any] = {}

        container._port_manager.inject_ports(use_case_cls, kwargs)
        container._handler_manager.inject_handlers(use_case_cls, kwargs)
        return use_case_cls(**kwargs)

    def _adapt_projection(self, projection_cls: type[TProjection], **overrides: Any) -> TProjection:
        container = self.with_adapters(**overrides) if overrides else self

        kwargs: dict[str, Any] = {}

        self._inject_projection(container, projection_cls, kwargs)
        container._port_manager.inject_ports(projection_cls, kwargs)
        return projection_cls(**kwargs)

    @staticmethod
    def _inject_projection(
        container: AdapterContainer,
        projection_cls: type[ProjectionBase],
        kwargs: dict[str, Any],
    ) -> None:
        if not container.sessions:
            return
        for field_name, field_info in projection_cls.__model_fields__.items():
            if field_name in kwargs:
                continue
            field_type = field_info.annotation
            if not _is_session_annotation(field_type):
                continue
            _validate_concrete_session(field_name, field_type, projection_cls.__name__)
            kwargs[field_name] = container._session_manager.get_session(field_type)
