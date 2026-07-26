from __future__ import annotations

import typing
from abc import abstractmethod
from functools import wraps
from typing import Any, Callable

from aod._internal.application.handler.handler import HandlerProtocol
from aod._internal.application.transaction import AsyncTransaction, Transaction
from aod._internal.core.async_utils import should_await
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.fields.fields import PrivateField
from aod._internal.core.infrastructure_exception import AbstractSessionTypeError
from aod._internal.infrastructure.session import AsyncSession, Session

_PROJECTION_WRAPPED_KEY = "__aod_projection_wrapped__"


def _raise_if_abstract_session(owner: str, field_name: str, tp: object) -> None:
    if tp is Session or tp is AsyncSession:
        raise AbstractSessionTypeError(owner, field_name, tp)


def _make_projection_wrapper(
    fn: Callable[..., Any],
    *,
    is_async: bool,
    is_write: bool,
    operation: str,
) -> Callable[..., Any]:
    only_read = not is_write

    if is_async:

        @wraps(fn)
        async def async_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            tx = AsyncTransaction(only_read=only_read, operation=self)
            for logger in self._loggers:
                tx.add_logger(logger)
            for bus in self._event_buses:
                tx.add_event_bus(bus)
            for session in self._sessions:
                tx.add_session(session)
            try:
                return await should_await(tx.run_transaction(fn, self, *args, **kwargs))
            finally:
                self.events = tx.get_events()

        return async_wrapper

    @wraps(fn)
    def sync_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        tx = Transaction(only_read=only_read, operation=self)
        for logger in self._loggers:
            tx.add_logger(logger)
        for bus in self._event_buses:
            tx.add_event_bus(bus)
        for session in self._sessions:
            tx.add_session(session)
        try:
            return tx.run_transaction(fn, self, *args, **kwargs)
        finally:
            self.events = tx.get_events()

    return sync_wrapper


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


class ReadProjectionBase(ProjectionBase):
    __skip_port_check__ = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_read: Callable[..., Any] | None = cls.__dict__.get("read")
        if original_read is not None and not getattr(original_read, _PROJECTION_WRAPPED_KEY, False):
            wrapped = _make_projection_wrapper(
                original_read, is_async=False, is_write=False, operation="read"
            )
            setattr(cls, "read", wrapped)
            setattr(wrapped, _PROJECTION_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)


class WriteProjectionBase(ProjectionBase):
    __skip_port_check__ = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_write: Callable[..., Any] | None = cls.__dict__.get("write")
        if original_write is not None and not getattr(
            original_write, _PROJECTION_WRAPPED_KEY, False
        ):
            wrapped = _make_projection_wrapper(
                original_write, is_async=False, is_write=True, operation="write"
            )
            setattr(cls, "write", wrapped)
            setattr(wrapped, _PROJECTION_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)


class AsyncReadProjectionBase(ProjectionBase):
    __skip_port_check__ = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_read: Callable[..., Any] | None = cls.__dict__.get("read")
        if original_read is not None and not getattr(original_read, _PROJECTION_WRAPPED_KEY, False):
            wrapped = _make_projection_wrapper(
                original_read, is_async=True, is_write=False, operation="read"
            )
            setattr(cls, "read", wrapped)
            setattr(wrapped, _PROJECTION_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)


class AsyncWriteProjectionBase(ProjectionBase):
    __skip_port_check__ = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_write: Callable[..., Any] | None = cls.__dict__.get("write")
        if original_write is not None and not getattr(
            original_write, _PROJECTION_WRAPPED_KEY, False
        ):
            wrapped = _make_projection_wrapper(
                original_write, is_async=True, is_write=True, operation="write"
            )
            setattr(cls, "write", wrapped)
            setattr(wrapped, _PROJECTION_WRAPPED_KEY, True)
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
