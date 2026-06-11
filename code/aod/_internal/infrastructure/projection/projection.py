from __future__ import annotations

from abc import abstractmethod
from functools import wraps
from typing import Any, Callable, TypeVar

from aod._internal.application.handler.handler import HandlerProtocol
from aod._internal.core.async_utils import should_await
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.event_emitter import EventCollector
from aod._internal.core.fields.fields import Field
from aod._internal.core.infrastructure_exception import InvalidPortFieldError
from aod._internal.infrastructure.commit_context import _CommitContext
from aod._internal.infrastructure.projection.models import ReadModel, WriteModel
from aod._internal.infrastructure.session import AsyncSession, Session

_PROJECTION_WRAPPED_KEY = "__aod_projection_wrapped__"
TReadModel = TypeVar("TReadModel", bound=ReadModel)
TWriteModel = TypeVar("TWriteModel", bound=WriteModel)


def _make_projection_wrapper(
    fn: Callable[..., Any],
    *,
    is_async: bool,
    is_write: bool,
    operation: str,
) -> Callable[..., Any]:
    if is_async:

        @wraps(fn)
        async def async_wrapper(self: Any, model: ReadModel | WriteModel) -> Any:
            token = _CommitContext.set(True) if is_write else None
            exception: BaseException | None = None
            try:
                if is_write and self.session is not None:
                    await should_await(self.session.begin())
                with EventCollector() as events:
                    try:
                        result = await should_await(fn(self, model))
                    except BaseException as e:
                        exception = e
                        result = None
                    self.events = list(events)
                if exception is not None:
                    if is_write and self.session is not None:
                        await should_await(self.session.rollback())
                    await should_await(
                        self.logger.error(
                            f"{type(self).__name__} {operation} failed with exception: {exception}"
                        )
                    )
                    raise exception
                await should_await(
                    self.logger.info(
                        f"{type(self).__name__} {operation} events", events=self.events
                    )
                )
                await should_await(self.cache.flush())
                await should_await(self.event_bus.publish(*self.events))
                await should_await(self.logger.info(f"{type(self).__name__} {operation} completed"))
                return result
            finally:
                if token is not None:
                    _CommitContext.reset(token)

        return async_wrapper

    @wraps(fn)
    def sync_wrapper(self: Any, model: ReadModel | WriteModel) -> Any:
        token = _CommitContext.set(True) if is_write else None
        exception: BaseException | None = None
        try:
            with EventCollector() as events:
                try:
                    result = fn(self, model)
                except BaseException as e:
                    exception = e
                    result = None
                self.events = list(events)
            if exception is not None:
                if is_write and self.session is not None and self.session.is_dirty():
                    self.session.rollback()
                self.logger.error(
                    f"{type(self).__name__} {operation} failed with exception: {exception}"
                )
                raise exception
            self.logger.info(f"{type(self).__name__} {operation} events", events=self.events)
            self.cache.flush()
            self.event_bus.publish(*self.events)
            self.logger.info(f"{type(self).__name__} {operation} completed")
            return result
        finally:
            if token is not None:
                _CommitContext.reset(token)

    return sync_wrapper


class ProjectionBase(BaseOperation):
    __skip_port_check__ = True
    __not_allowed_port_types__ = (HandlerProtocol,)
    session: Session | AsyncSession | None = None

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        session_fields = [
            name
            for name, tp in getattr(cls, "__annotations__", {}).items()
            if isinstance(tp, type) and issubclass(tp, (Session, AsyncSession))
        ]
        if len(session_fields) > 1:
            raise InvalidPortFieldError(
                session_fields[1],
                str(cls.__annotations__[session_fields[1]]),
            )


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
    session: Session | None = Field(default=None)

    @abstractmethod
    def write(self, model: TWriteModel) -> Any: ...


class ReadProjection(ReadProjectionBase):
    __skip_port_check__ = True
    session: Session | None = Field(default=None)

    @abstractmethod
    def read(self, model: TReadModel) -> Any: ...


class Projection(ReadProjection, WriteProjection):
    __skip_port_check__ = True

    @abstractmethod
    def read(self, model: TReadModel) -> Any: ...

    @abstractmethod
    def write(self, model: TWriteModel) -> Any: ...


class AsyncReadProjection(AsyncReadProjectionBase):
    __skip_port_check__ = True
    session: Session | AsyncSession | None = Field(default=None)

    @abstractmethod
    async def read(self, model: TReadModel) -> Any: ...


class AsyncWriteProjection(AsyncWriteProjectionBase):
    __skip_port_check__ = True
    session: Session | AsyncSession | None = Field(default=None)

    @abstractmethod
    async def write(self, model: TWriteModel) -> Any: ...


class AsyncProjection(AsyncReadProjection, AsyncWriteProjection):
    __skip_port_check__ = True

    @abstractmethod
    async def read(self, model: TReadModel) -> Any: ...

    @abstractmethod
    async def write(self, model: TWriteModel) -> Any: ...
