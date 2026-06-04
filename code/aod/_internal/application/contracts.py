from typing import Generic, TypeVar

from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.type_handlers.generic_utils import validate_generic_arg_is_subclass
from aod._internal.domain.entity import RootEntity

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")


class Command(BaseSealed, Generic[TEntity, TResult]):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        validate_generic_arg_is_subclass(cls, Command, RootEntity, arg_name="TEntity")


class Query(BaseSealed, Generic[TEntity, TResult]):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        validate_generic_arg_is_subclass(cls, Query, RootEntity, arg_name="TEntity")



