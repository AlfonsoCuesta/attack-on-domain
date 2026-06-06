from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from aod._internal.application.projection import ProjectionCommand, ProjectionQuery
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.type_handlers.generic_utils import validate_handler_subclass

PQ = TypeVar("PQ", bound=ProjectionQuery)
PC = TypeVar("PC", bound=ProjectionCommand)


class ProjectionQueryHandler(BaseSealed, Generic[PQ]):
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        validate_handler_subclass(cls, ProjectionQueryHandler, ProjectionQuery)

    @abstractmethod
    def handle(self, query: PQ) -> object: ...


class ProjectionCommandHandler(BaseSealed, Generic[PC]):
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        validate_handler_subclass(cls, ProjectionCommandHandler, ProjectionCommand)

    @abstractmethod
    def handle(self, command: PC) -> object: ...
