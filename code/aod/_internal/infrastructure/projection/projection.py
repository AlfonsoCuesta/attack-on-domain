from __future__ import annotations

from abc import abstractmethod
from functools import wraps
from typing import Any, Callable, cast

from aod._internal.core.application_exception import InvalidPortFieldError
from aod._internal.core.async_utils import should_await
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.base_validator import BaseValidator
from aod._internal.core.event_emitter import EventCollector
from aod._internal.core.fields.fields import Field
from aod._internal.infrastructure.commit_context import _CommitContext
from aod._internal.infrastructure.projection.models import ReadModel, WriteModel
from aod._internal.infrastructure.session import AsyncSession, Session

_PROJECTION_WRAPPED_KEY = "__aod_projection_wrapped__"


def _make_read_wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapper(self: Any, model: ReadModel) -> Any:
        exception: BaseException | None = None
        with EventCollector() as events:
            try:
                result = fn(self, model)
            except BaseException as e:
                exception = e
                result = None
            self.events = list(events)
        if exception is not None:
            self.logger.error(f"{type(self).__name__} read failed with exception: {exception}")
            raise exception
        self.logger.info(f"{type(self).__name__} read events", events=self.events)
        self.cache.flush()
        self.event_bus.publish(*self.events)
        self.logger.info(f"{type(self).__name__} read completed")
        return result

    return wrapper


def _make_write_wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapper(self: Any, model: WriteModel) -> Any:
        token = _CommitContext.set(True)
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
                if self.session is not None and self.session.is_dirty():
                    self.session.rollback()
                self.logger.error(f"{type(self).__name__} write failed with exception: {exception}")
                raise exception
            self.logger.info(f"{type(self).__name__} write events", events=self.events)
            self.cache.flush()
            self.event_bus.publish(*self.events)
            self.logger.info(f"{type(self).__name__} write completed")
            return result
        finally:
            _CommitContext.reset(token)

    return wrapper


def _make_async_read_wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    async def wrapper(self: Any, model: ReadModel) -> Any:
        exception: BaseException | None = None
        with EventCollector() as events:
            try:
                result = await should_await(fn(self, model))
            except BaseException as e:
                exception = e
                result = None
            self.events = list(events)
        if exception is not None:
            await should_await(
                self.logger.error(f"{type(self).__name__} read failed with exception: {exception}")
            )
            raise exception
        await should_await(
            self.logger.info(f"{type(self).__name__} read events", events=self.events)
        )
        await should_await(self.cache.flush())
        await should_await(self.event_bus.publish(*self.events))
        await should_await(self.logger.info(f"{type(self).__name__} read completed"))
        return result

    return wrapper


def _make_async_write_wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    async def wrapper(self: Any, model: WriteModel) -> Any:
        token = _CommitContext.set(True)
        exception: BaseException | None = None
        try:
            with EventCollector() as events:
                try:
                    result = await should_await(fn(self, model))
                except BaseException as e:
                    exception = e
                    result = None
                self.events = list(events)
            if exception is not None:
                if self.session is not None:
                    await should_await(self.session.rollback())
                await should_await(
                    self.logger.error(
                        f"{type(self).__name__} write failed with exception: {exception}"
                    )
                )
                raise exception
            await should_await(
                self.logger.info(f"{type(self).__name__} write events", events=self.events)
            )
            await should_await(self.cache.flush())
            await should_await(self.event_bus.publish(*self.events))
            await should_await(self.logger.info(f"{type(self).__name__} write completed"))
            return result
        finally:
            _CommitContext.reset(token)

    return wrapper


class ProjectionBase(BaseOperation):
    __skip_port_check__ = True
    session: Session | AsyncSession | None = None

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        sessions = []
        for subcls in cls.__mro__:
            if "__skip_port_check__" in subcls.__dict__:
                return
            subcls = cast(BaseValidator, subcls)
            for field_name, field_info in subcls.__model_fields__.items():
                if field_name not in cls.__annotations__:
                    continue

                tp = field_info.annotation
                if isinstance(tp, type) and issubclass(tp, (Session, AsyncSession)):
                    sessions.append(tp)
                    if len(sessions) > 1:
                        raise InvalidPortFieldError(
                            field_name,
                            cls.__name__,
                            str(field_info.annotation),
                        )
                    continue


class ReadProjectionBase(ProjectionBase):
    __skip_port_check__ = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_read: Callable[..., Any] | None = cls.__dict__.get("read")
        if original_read is not None and not getattr(original_read, _PROJECTION_WRAPPED_KEY, False):
            wrapped = _make_read_wrapper(original_read)
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
            wrapped = _make_write_wrapper(original_write)
            setattr(cls, "write", wrapped)
            setattr(wrapped, _PROJECTION_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)


class AsyncReadProjectionBase(ProjectionBase):
    __skip_port_check__ = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_read: Callable[..., Any] | None = cls.__dict__.get("read")
        if original_read is not None and not getattr(original_read, _PROJECTION_WRAPPED_KEY, False):
            wrapped = _make_async_read_wrapper(original_read)
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
            wrapped = _make_async_write_wrapper(original_write)
            setattr(cls, "write", wrapped)
            setattr(wrapped, _PROJECTION_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)


class WriteProjection(WriteProjectionBase):
    __skip_port_check__ = True
    session: Session | None = Field(default=None)

    @abstractmethod
    def write(self, model: WriteModel) -> Any: ...


class ReadProjection(ReadProjectionBase):
    __skip_port_check__ = True
    session: Session | None = Field(default=None)

    @abstractmethod
    def read(self, model: ReadModel) -> Any: ...


class Projection(ReadProjection, WriteProjection):
    __skip_port_check__ = True

    @abstractmethod
    def read(self, model: ReadModel) -> Any: ...

    @abstractmethod
    def write(self, model: WriteModel) -> Any: ...


class AsyncReadProjection(AsyncReadProjectionBase):
    __skip_port_check__ = True
    session: Session | AsyncSession | None = Field(default=None)

    @abstractmethod
    async def read(self, model: ReadModel) -> Any: ...


class AsyncWriteProjection(AsyncWriteProjectionBase):
    __skip_port_check__ = True
    session: Session | AsyncSession | None = Field(default=None)

    @abstractmethod
    async def write(self, model: WriteModel) -> Any: ...


class AsyncProjection(AsyncReadProjection, AsyncWriteProjection):
    __skip_port_check__ = True

    @abstractmethod
    async def read(self, model: ReadModel) -> Any: ...

    @abstractmethod
    async def write(self, model: WriteModel) -> Any: ...
