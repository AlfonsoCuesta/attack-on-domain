from __future__ import annotations

import typing
from abc import abstractmethod
from typing import Any

from aod._internal.application.handler.handler import HandlerProtocol
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.fields.fields import PrivateField
from aod._internal.core.infrastructure_exception import AbstractSessionTypeError
from aod._internal.infrastructure.session import AsyncSession, Session


def _raise_if_abstract_session(owner: str, field_name: str, tp: object) -> None:
    if tp is Session or tp is AsyncSession:
        raise AbstractSessionTypeError(owner, field_name, tp)


class ProjectionBase(BaseOperation):
    __skip_port_check__ = True
    __not_allowed_port_types__ = (HandlerProtocol,)
    _sessions: list[Session | AsyncSession] = PrivateField(default_factory=list)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._collect_sessions()

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        try:
            hints = typing.get_type_hints(cls)
        except Exception:
            return
        for field_name, tp in hints.items():
            _raise_if_abstract_session(cls.__name__, field_name, tp)

    def _collect_sessions(self) -> None:
        sessions: list[Session | AsyncSession] = []
        for field_name in self.__model_fields__:
            value = object.__getattribute__(self, field_name)
            if isinstance(value, (Session, AsyncSession)):
                sessions.append(value)
        object.__setattr__(self, "_sessions", sessions)

    def _begin_sessions(self) -> None:
        for session in self._sessions:
            session._begin()

    async def _begin_sessions_async(self) -> None:
        for session in self._sessions:
            if isinstance(session, AsyncSession):
                await session._begin()
            else:
                session._begin()


class ReadProjectionBase(ProjectionBase):
    __skip_port_check__ = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)


class WriteProjectionBase(ProjectionBase):
    __skip_port_check__ = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)


class AsyncReadProjectionBase(ProjectionBase):
    __skip_port_check__ = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)


class AsyncWriteProjectionBase(ProjectionBase):
    __skip_port_check__ = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)


class WriteProjection(WriteProjectionBase):
    __skip_port_check__ = True

    @abstractmethod
    def write(self, *args: Any, **kwargs: Any) -> Any: ...


class ReadProjection(ReadProjectionBase):
    __skip_port_check__ = True

    @abstractmethod
    def read(self, *args: Any, **kwargs: Any) -> Any: ...


class Projection(ReadProjection, WriteProjection):
    __skip_port_check__ = True

    @abstractmethod
    def read(self, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    def write(self, *args: Any, **kwargs: Any) -> Any: ...


class AsyncReadProjection(AsyncReadProjectionBase):
    __skip_port_check__ = True

    @abstractmethod
    async def read(self, *args: Any, **kwargs: Any) -> Any: ...


class AsyncWriteProjection(AsyncWriteProjectionBase):
    __skip_port_check__ = True

    @abstractmethod
    async def write(self, *args: Any, **kwargs: Any) -> Any: ...


class AsyncProjection(AsyncReadProjection, AsyncWriteProjection):
    __skip_port_check__ = True

    @abstractmethod
    async def read(self, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    async def write(self, *args: Any, **kwargs: Any) -> Any: ...
