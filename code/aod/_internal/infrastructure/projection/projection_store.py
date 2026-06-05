from __future__ import annotations

from typing import TypeVar, cast

from aod._internal.application.projection.projection import Projection
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_mro
from aod._internal.infrastructure.projection.projection_handler import ProjectionHandler

T = TypeVar("T")


class ProjectionStore(BaseSealed):
    handlers: list[ProjectionHandler] = Field(default_factory=list)
    _handlers: dict[type, ProjectionHandler] = PrivateField(default_factory=dict)

    def __post_init__(self) -> None:
        for h in self.handlers:
            p_type = get_generic_arg_from_mro(type(h), (ProjectionHandler,))
            if not isinstance(p_type, type) or not issubclass(p_type, Projection):
                msg = f"Cannot determine projection type for {type(h).__name__}"
                raise DomainException(msg)
            if p_type in self._handlers:
                msg = f"Duplicate handler for {p_type.__name__}"
                raise DomainException(msg)
            self._handlers[p_type] = h

    def projection(self, p: Projection[T]) -> T:
        handler = self._get_handler(p)
        return cast(T, handler.handle(p))

    def _get_handler(self, p: Projection[T]) -> ProjectionHandler:
        handler = self._handlers.get(type(p))
        if handler is None:
            msg = f"No handler registered for {type(p).__name__}"
            raise DomainException(msg)
        return handler
