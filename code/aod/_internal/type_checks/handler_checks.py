from __future__ import annotations

from typing import Any

from aod._internal.application.repository import Command, Query
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import (
    HandlerEntityMismatchError,
    HandlerTypeMismatchError,
    UnresolvableHandlerTypeError,
)
from aod._internal.core.type_handlers.generic_utils import (
    get_generic_arg_from_mro,
    get_generic_arg_from_orig_bases,
)


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
        raise HandlerTypeMismatchError(type(h).__name__, handler_type.__name__)


def validate_handler_entity(
    h: BaseSealed,
    handler_concrete_type: type[Command] | type[Query],
    repo_entity: type | None,
) -> None:
    h_entity = handler_type_entity(handler_concrete_type)
    if isinstance(h_entity, type) and isinstance(repo_entity, type) and h_entity is not repo_entity:
        raise HandlerEntityMismatchError(
            type(h).__name__, h_entity.__name__, repo_entity.__name__
        )


def extract_handler_type(
    handler: Any,
    handler_types: tuple[type, ...],
) -> type[Command | Query]:
    t = get_generic_arg_from_mro(type(handler), handler_types)
    if isinstance(t, type) and issubclass(t, (Command, Query)):
        return t
    raise UnresolvableHandlerTypeError(type(handler).__name__)
