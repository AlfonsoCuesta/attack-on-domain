from __future__ import annotations

from typing import cast

from aod._internal.core.infrastructure_exception import SessionNotFoundError
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.infrastructure.unit_of_work import AsyncUnitOfWork, UnitOfWork


class SessionManager:
    def __init__(
        self,
        sessions: set[type[Session] | type[AsyncSession]] | None = None,
    ) -> None:
        self._sessions: set[type[Session] | type[AsyncSession]] = (
            sessions if sessions is not None else set()
        )
        self._instances: dict[type[Session] | type[AsyncSession], Session | AsyncSession] = {}

    def get_session(
        self, session_cls: type[Session] | type[AsyncSession]
    ) -> Session | AsyncSession:
        if session_cls in self._instances:
            return self._instances[session_cls]
        for s in self._sessions:
            if isinstance(s, type) and issubclass(s, session_cls):
                instance = self._instantiate_session(s)
                self._instances[session_cls] = instance
                return instance
        raise SessionNotFoundError(session_cls)

    def _instantiate_session(
        self, session_cls: type[Session] | type[AsyncSession]
    ) -> Session | AsyncSession:
        return session_cls()

    def get_uow(self) -> UnitOfWork | AsyncUnitOfWork:
        sessions = set(self._instances.values())
        has_async = any(issubclass(s, AsyncSession) for s in self._sessions) or any(
            isinstance(s, AsyncSession) for s in self._instances
        )
        if has_async:
            return AsyncUnitOfWork(sessions=sessions)
        return UnitOfWork(sessions=cast(set[Session], sessions))

    def get_all_sessions(self) -> set[Session | AsyncSession]:
        return set(self._instances.values())
