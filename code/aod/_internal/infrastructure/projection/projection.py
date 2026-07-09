from __future__ import annotations

import typing
from abc import abstractmethod
from functools import wraps
from typing import Any, Callable

from aod._internal.application.handler.handler import HandlerProtocol
from aod._internal.core.async_utils import should_await
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.event_emitter import EventCollector
from aod._internal.core.fields.fields import PrivateField
from aod._internal.core.infrastructure_exception import AbstractSessionTypeError
from aod._internal.infrastructure.commit_context import _CommitContext
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
    if is_async:

        @wraps(fn)
        async def async_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            token = _CommitContext.set(True) if is_write else None
            exception: BaseException | None = None
            try:
                if is_write:
                    for session in self._sessions:
                        await should_await(session.begin())
                with EventCollector() as events:
                    try:
                        result = await should_await(fn(self, *args, **kwargs))
                    except BaseException as e:
                        exception = e
                        result = None
                    self.events = list(events)
                if exception is not None:
                    if is_write:
                        for session in self._sessions:
                            await should_await(session.rollback())
                    for logger in self._loggers:
                        await should_await(
                            logger.error(
                                f"{type(self).__name__} {operation} failed with exception: {exception}"
                            )
                        )
                    raise exception
                for logger in self._loggers:
                    await should_await(
                        logger.info(f"{type(self).__name__} {operation} events", events=self.events)
                    )
                for bus in self._event_buses:
                    await should_await(bus.publish(*self.events))
                for logger in self._loggers:
                    await should_await(logger.info(f"{type(self).__name__} {operation} completed"))
                return result
            finally:
                if token is not None:
                    _CommitContext.reset(token)

        return async_wrapper

    @wraps(fn)
    def sync_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        token = _CommitContext.set(True) if is_write else None
        exception: BaseException | None = None
        try:
            with EventCollector() as events:
                try:
                    result = fn(self, *args, **kwargs)
                except BaseException as e:
                    exception = e
                    result = None
                self.events = list(events)
            if exception is not None:
                if is_write:
                    for session in self._sessions:
                        if session.is_dirty():
                            session.rollback()
                for logger in self._loggers:
                    logger.error(
                        f"{type(self).__name__} {operation} failed with exception: {exception}"
                    )
                raise exception
            for logger in self._loggers:
                logger.info(f"{type(self).__name__} {operation} events", events=self.events)
            for bus in self._event_buses:
                bus.publish(*self.events)
            for logger in self._loggers:
                logger.info(f"{type(self).__name__} {operation} completed")
            return result
        finally:
            if token is not None:
                _CommitContext.reset(token)

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
