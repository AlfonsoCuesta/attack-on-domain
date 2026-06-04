from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from aod._internal.application.repository import Command, Query
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.type_handlers.generic_utils import validate_generic_arg_is_subclass

C = TypeVar("C", bound="Command")
Q = TypeVar("Q", bound="Query")


class CommandHandler(BaseSealed, Generic[C]):
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        validate_generic_arg_is_subclass(cls, CommandHandler, Command)

    @abstractmethod
    def handle(self, cmd: C) -> object: ...


class QueryHandler(BaseSealed, Generic[Q]):
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        validate_generic_arg_is_subclass(cls, QueryHandler, Query)

    @abstractmethod
    def handle(self, query: Q) -> object: ...
