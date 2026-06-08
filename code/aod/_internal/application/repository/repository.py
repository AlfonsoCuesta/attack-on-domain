from __future__ import annotations

from typing import Generic, Protocol, TypeVar, get_type_hints, runtime_checkable

from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import (
    InvalidCommandFieldTypeError,
    InvalidQueryResultTypeError,
)
from aod._internal.core.type_checking.extractors import extract_types_from_annotation
from aod._internal.core.type_handlers.generic_utils import (
    get_generic_arg_from_orig_bases,
    validate_generic_arg_is_subclass,
)
from aod._internal.core.type_utils import type_name
from aod._internal.domain.entity import Entity, RootEntity

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")


def _validate_fields_no_entity(cls: type) -> None:
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


def _validate_result_contains_root_entity(cls: type, query_type: type) -> None:
    result_type = get_generic_arg_from_orig_bases(cls, query_type, index=1)
    if result_type is None:
        return

    all_types = extract_types_from_annotation(result_type)
    if not any(isinstance(t, type) and issubclass(t, RootEntity) for t in all_types):
        raise InvalidQueryResultTypeError(cls.__name__, type_name(result_type))


class Command(BaseSealed, Generic[TEntity, TResult]):
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        validate_generic_arg_is_subclass(cls, Command, RootEntity, arg_name="TEntity")
        _validate_fields_no_entity(cls)


class Query(BaseSealed, Generic[TEntity, TResult]):
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        validate_generic_arg_is_subclass(cls, Query, RootEntity, arg_name="TEntity")
        _validate_fields_no_entity(cls)
        _validate_result_contains_root_entity(cls, Query)


@runtime_checkable
class Repository(Protocol, Generic[TEntity, TResult]):
    def command(self, command: Command[TEntity, TResult]) -> TResult: ...
    def query(self, query: Query[TEntity, TResult]) -> TResult: ...


@runtime_checkable
class AsyncRepository(Protocol, Generic[TEntity, TResult]):
    async def command(self, command: Command[TEntity, TResult]) -> TResult: ...
    async def query(self, query: Query[TEntity, TResult]) -> TResult: ...
