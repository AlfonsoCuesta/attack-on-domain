from typing import get_args, get_type_hints

from aod._internal.core.domain_exception import (
    InvalidCommandFieldTypeError,
    InvalidQueryResultTypeError,
)
from aod._internal.core.type_checking.extractors import extract_types_from_annotation
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases
from aod._internal.core.type_utils import type_name
from aod._internal.domain.entity import Entity, RootEntity


def validate_fields_no_entity(cls: type) -> None:
    own_field_names = cls.__dict__.get("__annotations__", {})
    if not own_field_names:
        return

    try:
        hints = get_type_hints(cls)
    except NameError:
        return

    for field_name in own_field_names:
        annotation = hints[field_name]
        for t in extract_types_from_annotation(annotation):
            if isinstance(t, type) and issubclass(t, Entity) and not issubclass(t, RootEntity):
                raise InvalidCommandFieldTypeError(cls.__name__, field_name, t.__name__)


def validate_result_contains_root_entity(cls: type, query_type: type) -> None:
    result_type = get_generic_arg_from_orig_bases(cls, query_type, index=1)
    if result_type is None:
        return

    all_types = extract_types_from_annotation(result_type)
    if not any(isinstance(t, type) and issubclass(t, RootEntity) for t in all_types):
        raise InvalidQueryResultTypeError(cls.__name__, type_name(result_type))


def extract_root_entity(repo: object) -> type | None:
    for base in getattr(type(repo), "__orig_bases__", ()):
        for arg in get_args(base):
            if isinstance(arg, type) and issubclass(arg, RootEntity):
                return arg
    return None
