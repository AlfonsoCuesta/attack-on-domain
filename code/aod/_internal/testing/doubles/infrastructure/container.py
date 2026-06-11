from __future__ import annotations

from typing import Any, TypeVar, cast

from aod._internal.application.contracts import Command, Query
from aod._internal.infrastructure.container import AdapterContainerBase
from aod._internal.infrastructure.handlers import (
    AsyncCommandHandler,
    AsyncQueryHandler,
    CommandHandler,
    QueryHandler,
)
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.testing.doubles.application.cache import AsyncSpyCache, SpyCache
from aod._internal.testing.doubles.application.event_bus import AsyncSpyEventBus, SpyEventBus
from aod._internal.testing.doubles.application.logger import AsyncSpyLogger, SpyLogger
from aod._internal.testing.doubles.application.unit_of_work import AsyncSpyUnitOfWork, SpyUnitOfWork
from aod._internal.testing.doubles.infrastructure.session import SpyAsyncSession, SpySession
from aod.exceptions import HandlerNotFoundError

T = TypeVar("T", bound=AdapterContainerBase)
HANDLER_TYPE_ALIAS = (
    type[QueryHandler] | type[AsyncQueryHandler] | type[CommandHandler] | type[AsyncCommandHandler]
)


class SpyBundle:
    """Access to all spy instances for assertions."""

    def __init__(self) -> None:
        self.sync_session = SpySession()
        self.async_session = SpyAsyncSession()
        self.logger = SpyLogger()
        self.async_logger = AsyncSpyLogger()
        self.event_bus = SpyEventBus()
        self.async_event_bus = AsyncSpyEventBus()
        self.cache = SpyCache()
        self.async_cache = AsyncSpyCache()
        self.uow = SpyUnitOfWork()
        self.async_uow = AsyncSpyUnitOfWork()


def spy_adapter_container(
    container: T,
    double_sessions: dict[type[Session] | type[AsyncSession], Session | AsyncSession] | None = None,
    double_handlers: dict[
        type[Command] | type[Query],
        type[CommandHandler] | type[AsyncCommandHandler] | type[QueryHandler] | type[AsyncQueryHandler],
    ]
    | None = None,
    **ports: Any,
) -> T:
    """Create a spy version of an AdapterContainer.

    All sessions are replaced by spy doubles. Specific sessions can be
    replaced with custom doubles via ``double_sessions``. Specific handlers
    can be replaced via ``double_handlers``. Additional port overrides can
    be passed as keyword arguments.

    Returns the container instance::

        container = spy_adapter_container(MyContainer)
        handler = container.get_handler(GetUser)
        handler.handle(GetUser(user_id=1))
        assert container.spy_bundle.logger.entries  # check what was logged

        container = spy_adapter_container(MyContainer, logger=my_logger)
        # Override specific ports

        container = spy_adapter_container(MyContainer, double_sessions={MySession: InMemorySession()})
        # Use custom in-memory session instances
    """
    spy_cls = _create_spy_adapter(
        type(container),
        double_sessions=double_sessions,
        double_handlers=double_handlers,
    )

    field_data: dict[str, Any] = {}
    for field_name in container.__model_fields__:
        field_data[field_name] = getattr(container, field_name)

    field_data.update(ports)

    instance = spy_cls(**field_data)
    return instance


def _create_spy_adapter(
    container_cls: type[T],
    double_sessions: dict[type[Session] | type[AsyncSession], Session | AsyncSession] | None = None,
    double_handlers: dict[
        type[Command] | type[Query],
        type[CommandHandler] | type[AsyncCommandHandler] | type[QueryHandler] | type[AsyncQueryHandler],
    ]
    | None = None,
) -> type[T]:
    if double_sessions is None:
        double_sessions = {}
    if double_handlers is None:
        double_handlers = {}

    bundle = SpyBundle()

    def _instantiate_session(
        self: Any, session_cls: type[Session] | type[AsyncSession]
    ) -> Session | AsyncSession:
        if session_cls in self._double_sessions:
            return self._double_sessions[session_cls]
        if issubclass(session_cls, AsyncSession):
            return self._spy_bundle.async_session
        return self._spy_bundle.sync_session

    def _find_handler(self, contract: type[Command] | type[Query]) -> HANDLER_TYPE_ALIAS:
        if contract in self._double_handlers:
            return self._double_handlers[contract]

        for h_cls in self.handlers:
            if self._contract_from_handler(h_cls) is contract:
                return h_cls
        raise HandlerNotFoundError("handler", contract.__name__)

    @property
    def _spy_property(self) -> SpyBundle:
        return self._spy_bundle

    spy_cls = cast(
        type[T],
        type(
            f"Spy{container_cls.__name__}",
            (container_cls,),
            {
                "_spy_bundle": bundle,
                "spy_bundle": _spy_property,
                "_double_sessions": double_sessions,
                "_double_handlers": double_handlers,
                "_instantiate_session": _instantiate_session,
                "_find_handler": _find_handler,
            },
        ),
    )

    return spy_cls
