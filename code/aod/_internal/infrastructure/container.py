from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.infrastructure.handlers import (
    AsyncCommandHandler,
    AsyncQueryHandler,
    CommandHandler,
    QueryHandler,
)
from aod._internal.infrastructure.projection import (
    AsyncProjectionCommandHandler,
    AsyncProjectionQueryHandler,
    ProjectionCommandHandler,
    ProjectionQueryHandler,
)
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.infrastructure.unit_of_work import UnitOfWork

AnyHandler = (
    type[CommandHandler]
    | type[QueryHandler]
    | type[AsyncCommandHandler]
    | type[AsyncQueryHandler]
    | type[ProjectionQueryHandler]
    | type[ProjectionCommandHandler]
    | type[AsyncProjectionQueryHandler]
    | type[AsyncProjectionCommandHandler]
)


class AdapterContainer(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    session: Session | AsyncSession | None = None
    logger: Logger | AsyncLogger | None = None
    event_bus: EventBus | AsyncEventBus | None = None
    cache: Cache | AsyncCache | None = None
    handlers: list[AnyHandler] = []

    def _collect_sessions(self) -> list[Session | AsyncSession]:
        seen: list[Session | AsyncSession] = []
        for h_cls in self.handlers:
            instance = h_cls(session=self.session)
            s = getattr(instance, "session", None)
            if s is not None and not any(s is x for x in seen):
                seen.append(s)
        return seen

    @property
    def uow(self) -> UnitOfWork:
        return UnitOfWork(sessions=set(self._collect_sessions()))

    def with_(self, **overrides: Any) -> AdapterContainer:
        current = self.model_dump()
        current.update(overrides)
        return self.__class__(**current)