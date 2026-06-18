from __future__ import annotations

from typing import get_type_hints

from aod._internal.application.port import Port
from aod._internal.core.domain_exception import DuplicateDomainTypeError
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases
from aod._internal.infrastructure.handlers.handlers import BaseHandler
from aod._internal.infrastructure.projection import ProjectionBase
from aod._internal.infrastructure.session import AsyncSession, Session

type HandlerType = type[BaseHandler]
type ProjectionType = type[ProjectionBase]
type SessionType = type[Session] | type[AsyncSession]
type PortType = type[Port]


class Infrastructure:
    def __init__(
        self,
        handlers: list[HandlerType] | None = None,
        projections: list[ProjectionType] | None = None,
        ports: list[PortType] | None = None,
    ):
        if handlers is None:
            handlers = []
        if projections is None:
            projections = []
        if ports is None:
            ports = []

        self._check_duplicate_contracts(handlers)

        sessions = self._extract_sessions(handlers, projections)

        self.handlers: tuple[HandlerType, ...] = tuple(handlers)
        self.projections: tuple[ProjectionType, ...] = tuple(projections)
        self.sessions: tuple[SessionType, ...] = tuple(sessions)
        self.ports: tuple[PortType, ...] = tuple(ports)

    @staticmethod
    def _check_duplicate_contracts(handlers: list[HandlerType]) -> None:
        seen: dict[type, HandlerType] = {}

        for handler_cls in handlers:
            for base in getattr(handler_cls, "__orig_bases__", ()):
                origin = getattr(base, "__origin__", None)
                if origin is None:
                    continue
                origin_name = getattr(origin, "__name__", "")
                if origin_name in (
                    "CommandHandler",
                    "QueryHandler",
                    "AsyncCommandHandler",
                    "AsyncQueryHandler",
                    "CommandPort",
                    "QueryPort",
                ):
                    contract = get_generic_arg_from_orig_bases(handler_cls, origin)
                    if contract is not None and contract in seen:
                        raise DuplicateDomainTypeError(
                            contract.__name__,
                            "Contract",
                            f"handled by both {seen[contract].__name__} and {handler_cls.__name__}",
                        )
                    if contract is not None:
                        seen[contract] = handler_cls

    @staticmethod
    def _extract_sessions(
        handlers: list[HandlerType],
        projections: list[ProjectionType],
    ) -> list[SessionType]:
        sessions: list[SessionType] = []

        for cls in handlers + projections:
            hints = get_type_hints(cls)
            session_type = hints.get("session")
            if session_type is None:
                continue
            origin = getattr(session_type, "__origin__", None)
            if origin is not None:
                args = getattr(session_type, "__args__", ())
                for arg in args:
                    if isinstance(arg, type) and issubclass(arg, (Session, AsyncSession)):
                        sessions.append(arg)
            elif isinstance(session_type, type) and issubclass(
                session_type, (Session, AsyncSession)
            ):
                sessions.append(session_type)

        return list(set(sessions))
