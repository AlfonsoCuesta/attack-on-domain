from __future__ import annotations

from types import UnionType
from typing import Any, ClassVar, Self, Union, cast, get_args, get_origin, get_type_hints

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.cache.null_cache import NullCache
from aod._internal.application.contracts import Command, Query
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.event_bus.null_event_bus import NullEventBus
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.application.logger.null_logger import NullLogger
from aod._internal.application.port import Port
from aod._internal.core.base_behaviour import BaseBehaviour
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
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.infrastructure.unit_of_work import AsyncUnitOfWork, UnitOfWork

_SYNC_HANDLERS = CommandHandler | QueryHandler
_ASYNC_HANDLERS = AsyncCommandHandler | AsyncQueryHandler

AnyHandler = (
    type[CommandHandler] | type[QueryHandler] | type[AsyncCommandHandler] | type[AsyncQueryHandler]
)


def _is_port_type(tp: object) -> bool:
    origin = get_origin(tp)
    if origin is UnionType or origin is Union:
        return False
    if origin is not None:
        return any(isinstance(a, type) and issubclass(a, Port) for a in get_args(tp))
    return isinstance(tp, type) and issubclass(tp, Port)


class AdapterContainerBase(BaseBehaviour):
    sessions: set[type[Session] | type[AsyncSession]] = Field(default_factory=set)
    logger: Logger | AsyncLogger = Field(default_factory=NullLogger)
    event_bus: EventBus | AsyncEventBus = Field(default_factory=NullEventBus)
    cache: Cache | AsyncCache = Field(default_factory=NullCache)
    handlers: list[AnyHandler] = Field(default_factory=list)
    _sessions_needed: dict[type[Session] | type[AsyncSession], Session | AsyncSession] = (
        PrivateField(default_factory=dict)
    )
    _ports_by_type: dict[type[Port], Port] = PrivateField(default_factory=dict)

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        hints = get_type_hints(cls)
        for name, tp in hints.items():
            if (
                name.startswith("_")
                or name in AdapterContainerBase.__model_fields__
                or get_origin(tp) is ClassVar
            ):
                continue
            if not _is_port_type(tp):
                raise InvalidPortFieldError(name, str(tp))

    def __post_init__(self) -> None:
        self._validate_no_duplicate_handlers()
        hints = get_type_hints(self.__class__)
        for name in self.__model_fields__:
            tp = hints.get(name)
            if tp is not None and _is_port_type(tp):
                self._ports_by_type[tp] = getattr(self, name)

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

    def get_port(self, port: type[Port]) -> Port:
        port_instance = self._get_port_instance(port)
        if port_instance is not None:
            return port_instance
        raise PortNotFoundError(port)

    def _get_port_instance(self, port: type[Port]) -> Port | None:
        return self._ports_by_type.get(port, None)

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
