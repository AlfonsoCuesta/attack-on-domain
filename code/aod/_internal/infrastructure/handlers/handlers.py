from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from aod._internal.application.repository import Command, Query

from .base_handler import BaseHandler

C = TypeVar("C", bound="Command")
Q = TypeVar("Q", bound="Query")


class CommandHandler(BaseHandler, Generic[C]):
    @abstractmethod
    def handle(self, cmd: C) -> object: ...


class QueryHandler(BaseHandler, Generic[Q]):
    @abstractmethod
    def handle(self, query: Q) -> object: ...
