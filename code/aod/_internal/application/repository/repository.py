from __future__ import annotations

from typing import Generic, Protocol, TypeVar, runtime_checkable

from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.type_handlers.generic_utils import validate_generic_arg_is_subclass
from aod._internal.domain.entity import RootEntity
from aod._internal.type_checks.contract_checks import (
    validate_fields_no_entity,
    validate_result_contains_root_entity,
)

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")


class Command(BaseSealed, Generic[TEntity, TResult]):
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        validate_generic_arg_is_subclass(cls, Command, RootEntity, arg_name="TEntity")
        validate_fields_no_entity(cls)


class Query(BaseSealed, Generic[TEntity, TResult]):
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        validate_generic_arg_is_subclass(cls, Query, RootEntity, arg_name="TEntity")
        validate_fields_no_entity(cls)
        validate_result_contains_root_entity(cls, Query)


@runtime_checkable
class Repository(Protocol, Generic[TEntity, TResult]):
    def command(self, command: Command[TEntity, TResult]) -> TResult: ...
    def query(self, query: Query[TEntity, TResult]) -> TResult: ...
