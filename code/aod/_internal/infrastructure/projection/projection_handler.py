from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from aod._internal.application.projection import ProjectionCommand, ProjectionQuery
from aod._internal.infrastructure.handlers.base_handler import BaseHandler

PQ = TypeVar("PQ", bound=ProjectionQuery)
PC = TypeVar("PC", bound=ProjectionCommand)


class ProjectionQueryHandler(BaseHandler, Generic[PQ]):
    @abstractmethod
    def handle(self, query: PQ) -> object: ...


class ProjectionCommandHandler(BaseHandler, Generic[PC]):
    @abstractmethod
    def handle(self, command: PC) -> object: ...
