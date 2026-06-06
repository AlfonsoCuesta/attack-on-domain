from __future__ import annotations

from typing import ClassVar, TypeVar, cast

from aod._internal.application.projection import ProjectionCommand, ProjectionQuery
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_mro
from aod._internal.infrastructure.projection.projection_handler import (
    ProjectionCommandHandler,
    ProjectionQueryHandler,
)

T = TypeVar("T")

_PROJECTION_HANDLERS = (ProjectionQueryHandler, ProjectionCommandHandler)


class ProjectionStore(BaseSealed):
    handlers: list[ProjectionQueryHandler | ProjectionCommandHandler] = Field(default_factory=list)
    _query_handlers: dict[type, ProjectionQueryHandler] = PrivateField(default_factory=dict)
    _command_handlers: dict[type, ProjectionCommandHandler] = PrivateField(default_factory=dict)
    __allowed_handlers__: ClassVar[tuple[type, ...]] = _PROJECTION_HANDLERS

    def _register_handler(self, h: ProjectionQueryHandler | ProjectionCommandHandler) -> None:
        p_type = get_generic_arg_from_mro(type(h), self.__allowed_handlers__)
        if not isinstance(p_type, type):
            msg = f"Cannot determine projection type for {type(h).__name__}"
            raise DomainException(msg)
        if issubclass(p_type, ProjectionQuery):
            if p_type in self._query_handlers:
                msg = f"Duplicate handler for {p_type.__name__}"
                raise DomainException(msg)
            self._query_handlers[p_type] = cast(ProjectionQueryHandler, h)
        elif issubclass(p_type, ProjectionCommand):
            if p_type in self._command_handlers:
                msg = f"Duplicate handler for {p_type.__name__}"
                raise DomainException(msg)
            self._command_handlers[p_type] = cast(ProjectionCommandHandler, h)

    def __post_init__(self) -> None:
        for h in self.handlers:
            self._register_handler(h)

    def query(self, query: ProjectionQuery[T]) -> T:
        handler = self._query_handlers.get(type(query))
        if handler is None:
            msg = f"No handler registered for {type(query).__name__}"
            raise DomainException(msg)
        return cast(T, handler.handle(query))

    def command(self, command: ProjectionCommand[T]) -> T:
        handler = self._command_handlers.get(type(command))
        if handler is None:
            msg = f"No handler registered for {type(command).__name__}"
            raise DomainException(msg)
        return cast(T, handler.handle(command))
