from __future__ import annotations

from typing import overload

from aod._internal.application.repository import Command, Query
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.type_handlers.generic_utils import (
    get_generic_arg_from_mro,
    get_generic_arg_from_orig_bases,
)
from aod._internal.infrastructure.handlers.async_ import CommandHandler, QueryHandler


def handler_type_entity(handler_type: type[Command] | type[Query]) -> type | None:
    entity = get_generic_arg_from_orig_bases(handler_type, Command)
    if entity is None:
        entity = get_generic_arg_from_orig_bases(handler_type, Query)
    return entity if isinstance(entity, type) else None


def validate_handler_type(
    h: BaseSealed,
    handler_type: type[BaseSealed],
) -> None:
    if not issubclass(type(h), handler_type):
        msg = f"Handler {type(h).__name__} does not handle a {handler_type.__name__}"
        raise DomainException(msg)


def validate_handler_entity(
    h: BaseSealed,
    handler_concrete_type: type[Command] | type[Query],
    repo_entity: type | None,
) -> None:
    h_entity = handler_type_entity(handler_concrete_type)
    if isinstance(h_entity, type) and isinstance(repo_entity, type) and h_entity is not repo_entity:
        msg = f"Handler {type(h).__name__} handles entity {h_entity.__name__}, but repository is for entity {repo_entity.__name__}"
        raise DomainException(msg)


@overload
def extract_handler_type(handler: CommandHandler) -> type[Command]: ...


@overload
def extract_handler_type(handler: QueryHandler) -> type[Query]: ...


def extract_handler_type(
    handler: CommandHandler | QueryHandler,
) -> type[Command | Query]:
    t = get_generic_arg_from_mro(type(handler), (CommandHandler, QueryHandler))
    if isinstance(t, type) and issubclass(t, (Command, Query)):
        return t
    msg = f"Cannot determine handler type for {type(handler).__name__}"
    raise DomainException(msg)
