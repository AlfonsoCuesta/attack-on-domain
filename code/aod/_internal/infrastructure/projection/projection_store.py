from __future__ import annotations

from typing import Any, ClassVar, TypeVar, cast

from aod._internal.application.projection import ProjectionCommand, ProjectionQuery, ReadModel
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_mro
from aod._internal.infrastructure.projection.projection_handler import (
    ProjectionCommandHandler,
    ProjectionQueryHandler,
)

T = TypeVar("T", bound=ReadModel | None)


class _BaseProjectionStore(BaseSealed):
    handlers: list[Any] = Field(default_factory=list)
    _query_handlers: dict[type, Any] = PrivateField(default_factory=dict)
    _command_handlers: dict[type, Any] = PrivateField(default_factory=dict)
    __allowed_handler_types__: ClassVar[tuple[type, ...]] = ()

    def _register_handler(self, h: Any) -> None:
        p_type = get_generic_arg_from_mro(type(h), self.__allowed_handler_types__)
        if not isinstance(p_type, type):
            msg = f"Cannot determine projection type for {type(h).__name__}"
            raise DomainException(msg)
        if issubclass(p_type, ProjectionQuery):
            if p_type in self._query_handlers:
                msg = f"Duplicate handler for {p_type.__name__}"
                raise DomainException(msg)
            self._query_handlers[p_type] = h
        elif issubclass(p_type, ProjectionCommand):
            if p_type in self._command_handlers:
                msg = f"Duplicate handler for {p_type.__name__}"
                raise DomainException(msg)
            self._command_handlers[p_type] = h

    def __post_init__(self) -> None:
        for h in self.handlers:
            self._register_handler(h)


class ProjectionStore(_BaseProjectionStore):
    handlers: list[ProjectionQueryHandler | ProjectionCommandHandler] = Field(default_factory=list)
    _query_handlers: dict[type, ProjectionQueryHandler] = PrivateField(default_factory=dict)
    _command_handlers: dict[type, ProjectionCommandHandler] = PrivateField(default_factory=dict)
    __allowed_handler_types__ = (ProjectionQueryHandler, ProjectionCommandHandler)

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
