from __future__ import annotations

from types import UnionType
from typing import Any, ClassVar, Self, TypeVar, Union, cast, get_args, get_origin, get_type_hints

from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler.handler import HandlerProtocol
from aod._internal.application.port import Port
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.core.application_exception import InvalidHandlerPortFieldError
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.core.infrastructure_exception import (
    DuplicateHandlerError,
    HandlerModelError,
    HandlerNotFoundError,
    InvalidPortFieldError,
    PortNotFoundError,
    SessionNotFoundError,
)
from aod._internal.infrastructure.handlers import (
    AsyncCommandHandler,
    AsyncQueryHandler,
    CommandHandler,
    QueryHandler,
)
from aod._internal.infrastructure.handlers.handlers import AsyncBaseHandler
from aod._internal.infrastructure.projection import ProjectionBase
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.infrastructure.unit_of_work import AsyncUnitOfWork, UnitOfWork

_SYNC_HANDLERS = CommandHandler | QueryHandler
_ASYNC_HANDLERS = AsyncCommandHandler | AsyncQueryHandler

AnyHandler = (
    type[CommandHandler] | type[QueryHandler] | type[AsyncCommandHandler] | type[AsyncQueryHandler]
)

TUseCase = TypeVar("TUseCase", bound=UseCase | AsyncUseCase)
TProjection = TypeVar("TProjection", bound=ProjectionBase)


def _is_port_type(tp: object) -> bool:
    origin = get_origin(tp)
    if origin is UnionType or origin is Union:
        return False
    if origin is not None:
        return any(isinstance(a, type) and issubclass(a, Port) for a in get_args(tp))
    return isinstance(tp, type) and issubclass(tp, Port)


def extract_port_type(tp: object) -> type[Port] | None:
    origin = get_origin(tp)
    if origin is not None:
        tp = origin
    if isinstance(tp, type) and issubclass(tp, Port) and not issubclass(tp, HandlerProtocol):
        return tp
    return None


def _is_session_annotation(tp: object) -> bool:
    return isinstance(tp, type) and issubclass(tp, (Session, AsyncSession))


class AdapterContainer(BaseBehaviour):
    sessions: set[type[Session] | type[AsyncSession]] = Field(default_factory=set)
    handlers: list[AnyHandler] = Field(default_factory=list)
    _ports_by_name: dict[str, Port] = PrivateField(default_factory=dict)
    _sessions_needed: dict[type[Session] | type[AsyncSession], Session | AsyncSession] = (
        PrivateField(default_factory=dict)
    )

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        hints = get_type_hints(cls)
        for name, tp in hints.items():
            if (
                name.startswith("_")
                or name in AdapterContainer.__model_fields__
                or get_origin(tp) is ClassVar
            ):
                continue
            if not _is_port_type(tp):
                raise InvalidPortFieldError(name, str(tp))

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._validate_no_duplicate_handlers()
        self._build_port_index()

    def _build_port_index(self) -> None:
        hints = get_type_hints(self.__class__)
        for name in self.__model_fields__:
            tp = hints.get(name)
            if tp is None or not _is_port_type(tp):
                continue
            value = getattr(self, name)
            if isinstance(value, Port):
                self._ports_by_name[name] = value

    @staticmethod
    def _contract_from_handler(h_cls: AnyHandler) -> type[Command] | type[Query]:
        hints = get_type_hints(h_cls.handle)
        for param_type in hints.values():
            if isinstance(param_type, type) and issubclass(param_type, (Command, Query)):
                return param_type
        raise HandlerModelError(h_cls, "handle")

    def _validate_no_duplicate_handlers(self) -> None:
        seen: set[type[Command] | type[Query]] = set()
        for h_cls in self.handlers:
            contract = self._contract_from_handler(h_cls)
            if contract in seen:
                raise DuplicateHandlerError(contract.__name__)
            seen.add(contract)

    def get_uow(self) -> UnitOfWork | AsyncUnitOfWork:
        sessions = set(self._sessions_needed.values())
        has_async = any(issubclass(s, AsyncSession) for s in self.sessions) or any(
            isinstance(s, AsyncSession) for s in self._sessions_needed
        )
        if has_async:
            return AsyncUnitOfWork(sessions=sessions)
        return UnitOfWork(sessions=cast(set[Session], sessions))

    def with_adapters(self, **overrides: Any) -> Self:
        return self.copy(**overrides)

    def get_port(self, name: str) -> Port:
        if name in self._ports_by_name:
            return self._ports_by_name[name]
        raise PortNotFoundError(name)

    def _find_handler(self, contract: type[Command] | type[Query]) -> AnyHandler:
        for h_cls in self.handlers:
            if self._contract_from_handler(h_cls) is contract:
                return h_cls
        raise HandlerNotFoundError("handler", contract.__name__)

    def get_handler(
        self, contract: type[Command] | type[Query]
    ) -> CommandHandler | AsyncCommandHandler | QueryHandler | AsyncQueryHandler:
        handler = self._find_handler(contract)
        cls_hints = get_type_hints(handler)
        try:
            session_type = cls_hints["session"]
        except KeyError:
            raise HandlerModelError(handler, "session")
        session: Session | AsyncSession | None = None
        if session_type is not type(None):
            session_cls = session_type
            session = self.get_session(session_cls)

        return self._instantiate_handler(handler, session)

    def _instantiate_handler(
        self,
        handler: type[_ASYNC_HANDLERS | _SYNC_HANDLERS],
        session: Session | AsyncSession | None,
    ) -> _ASYNC_HANDLERS | _SYNC_HANDLERS:
        if issubclass(handler, AsyncBaseHandler):
            return cast(_ASYNC_HANDLERS, handler(session=cast(AsyncSession | None, session)))
        return cast(_SYNC_HANDLERS, handler(session=cast(Session | None, session)))

    def _instantiate_session(
        self, session_cls: type[Session] | type[AsyncSession]
    ) -> Session | AsyncSession:
        return session_cls()

    def get_session(
        self, session_cls: type[Session] | type[AsyncSession]
    ) -> Session | AsyncSession:
        if session_cls in self._sessions_needed:
            return self._sessions_needed[session_cls]
        for s in self.sessions:
            if isinstance(s, type) and issubclass(s, session_cls):
                instance = self._instantiate_session(s)
                self._sessions_needed[session_cls] = instance
                return instance
        raise SessionNotFoundError(session_cls)

    # --- Dependency injection ---

    def adapt_use_case(self, use_case_cls: type[TUseCase], **overrides: Any) -> TUseCase:
        container = self.with_adapters(**overrides) if overrides else self

        kwargs: dict[str, Any] = {
            "uow": container.get_uow(),
        }

        container._inject_ports(use_case_cls, kwargs)
        container._inject_handlers(use_case_cls, kwargs)
        return use_case_cls(**kwargs)

    def adapt_projection(self, projection_cls: type[TProjection], **overrides: Any) -> TProjection:
        container = self.with_adapters(**overrides) if overrides else self

        kwargs: dict[str, Any] = {}

        container._inject_projection(projection_cls, kwargs)
        container._inject_ports(projection_cls, kwargs)
        return projection_cls(**kwargs)

    def _inject_ports(self, operation_cls: type[BaseOperation], kwargs: dict[str, Any]) -> None:
        for field_name, field_info in operation_cls.__model_fields__.items():
            if field_name in kwargs:
                continue
            field_type = field_info.annotation
            if field_type is None or not _is_port_type(field_type):
                continue
            if field_name not in self._ports_by_name:
                raise PortNotFoundError(field_name)
            kwargs[field_name] = self._ports_by_name[field_name]

    def _inject_handlers(self, use_case_cls: type[TUseCase], kwargs: dict[str, Any]) -> None:
        for field_name, field_info in use_case_cls.__model_fields__.items():
            if field_name in kwargs:
                continue
            field_type = field_info.annotation
            origin = get_origin(field_type)
            if (
                origin is None
                or not isinstance(origin, type)
                or not issubclass(origin, HandlerProtocol)
            ):
                continue
            args = get_args(field_type)
            if not args:
                raise InvalidHandlerPortFieldError(field_name, use_case_cls.__name__)
            contract = args[0]
            if isinstance(contract, type) and issubclass(contract, (Command, Query)):
                kwargs[field_name] = self.get_handler(contract)

    def _inject_projection(
        self, projection_cls: type[ProjectionBase], kwargs: dict[str, Any]
    ) -> None:
        if not self.sessions:
            return
        for field_name, field_info in projection_cls.__model_fields__.items():
            if field_name in kwargs:
                continue
            field_type = field_info.annotation
            if field_type is None:
                continue
            if not _is_session_annotation(field_type):
                continue
            kwargs[field_name] = self.get_session(field_type)
