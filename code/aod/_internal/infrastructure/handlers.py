from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar, overload

from aod._internal.application.contracts import Command, Projection, Query
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.type_handlers.generic_utils import (
    get_generic_arg_from_mro,
    validate_generic_arg_is_subclass,
)

C = TypeVar("C", bound="Command")
Q = TypeVar("Q", bound="Query")
P = TypeVar("P", bound="Projection")


class CommandHandler(BaseSealed, Generic[C]):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        from aod._internal.application.contracts import Command

        validate_generic_arg_is_subclass(cls, CommandHandler, Command)

    @abstractmethod
    def handle(self, cmd: C) -> object: ...


class QueryHandler(BaseSealed, Generic[Q]):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        from aod._internal.application.contracts import Query

        validate_generic_arg_is_subclass(cls, QueryHandler, Query)

    @abstractmethod
    def handle(self, query: Q) -> object: ...


class ProjectionHandler(BaseSealed, Generic[P]):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        validate_generic_arg_is_subclass(cls, ProjectionHandler, Projection)

    @abstractmethod
    def handle(self, projection: P) -> object: ...


@overload
def _extract_handler_type(handler: CommandHandler) -> type[Command]: ...


@overload
def _extract_handler_type(handler: QueryHandler) -> type[Query]: ...


@overload
def _extract_handler_type(handler: ProjectionHandler) -> type[Projection]: ...


def _extract_handler_type(
    handler: CommandHandler | QueryHandler | ProjectionHandler,
) -> type[Command | Query | Projection]:
    from aod._internal.application.contracts import Command, Projection, Query

    t = get_generic_arg_from_mro(type(handler), (CommandHandler, QueryHandler, ProjectionHandler))
    if isinstance(t, type) and issubclass(t, (Command, Query, Projection)):
        return t
    msg = f"Cannot determine handler type for {type(handler).__name__}"
    raise DomainException(msg)
