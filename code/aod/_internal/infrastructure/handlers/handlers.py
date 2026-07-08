from __future__ import annotations

from abc import abstractmethod
import typing
from typing import Generic, TypeVar

from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler import (
    AsyncCommandPort,
    AsyncQueryPort,
    CommandPort,
    QueryPort,
)
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.infrastructure_exception import AbstractSessionTypeError
from aod._internal.infrastructure.session import AsyncSession, Session

TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)


class BaseHandler(BaseBehaviour):
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        try:
            hints = typing.get_type_hints(cls)
        except Exception:
            return
        for field_name, tp in hints.items():
            _raise_if_abstract_session(cls.__name__, field_name, tp)


def _raise_if_abstract_session(owner: str, field_name: str, tp: object) -> None:
    if tp is Session or tp is AsyncSession:
        raise AbstractSessionTypeError(owner, field_name, tp)


class AsyncBaseHandler(BaseHandler):
    pass


class CommandHandler(BaseHandler, CommandPort, Generic[TCommand]):
    @abstractmethod
    def handle(self, command: TCommand) -> object: ...  # ty:ignore[invalid-method-override]


class QueryHandler(BaseHandler, QueryPort, Generic[TQuery]):
    @abstractmethod
    def handle(self, query: TQuery) -> object: ...  # ty:ignore[invalid-method-override]


class AsyncCommandHandler(AsyncBaseHandler, AsyncCommandPort, Generic[TCommand]):
    @abstractmethod
    async def handle(self, command: TCommand) -> object: ...  # ty:ignore[invalid-method-override]


class AsyncQueryHandler(AsyncBaseHandler, AsyncQueryPort, Generic[TQuery]):
    @abstractmethod
    async def handle(self, query: TQuery) -> object: ...  # ty:ignore[invalid-method-override]
