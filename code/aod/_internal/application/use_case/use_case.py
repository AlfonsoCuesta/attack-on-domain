from __future__ import annotations

from abc import abstractmethod
from typing import Any

from aod._internal.core.base_operation import BaseOperation
from aod._internal.infrastructure.session import AsyncSession, Session


class UseCase(BaseOperation):
    __skip_port_check__ = True
    __not_allowed_port_types__ = (Session, AsyncSession)

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any: ...


class AsyncUseCase(BaseOperation):
    __skip_port_check__ = True
    __not_allowed_port_types__ = (Session, AsyncSession)

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any: ...
