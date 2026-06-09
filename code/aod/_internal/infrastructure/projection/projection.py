from __future__ import annotations

from abc import abstractmethod
from functools import wraps
from typing import Any, Callable

from aod._internal.core.base_operation import BaseOperation
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
        self.logger.info(f"{type(self).__name__} read events", events=self.events)
        if exception is not None:
            self.logger.error(f"{type(self).__name__} read failed with exception: {exception}")
            raise exception
        self.event_bus.publish(*self.events)
        self.logger.info(f"{type(self).__name__} read completed", events=len(self.events))
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
            self.logger.info(f"{type(self).__name__} write events", events=self.events)
            if exception is not None:
                if self.session is not None:
                    self.session.rollback()
                self.logger.error(f"{type(self).__name__} write failed with exception: {exception}")
                raise exception
            self.event_bus.publish(*self.events)
            self.logger.info(f"{type(self).__name__} write completed", events=len(self.events))
            return result
        finally:
            _CommitContext.reset(token)

    return wrapper


class ProjectionBase(BaseOperation):
    pass


class ReadProjectionBase(ProjectionBase):
    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_read: Callable[..., Any] | None = cls.__dict__.get("read")
        if original_read is not None and not getattr(original_read, _PROJECTION_WRAPPED_KEY, False):
            wrapped = _make_read_wrapper(original_read)
            setattr(cls, "read", wrapped)
            setattr(wrapped, _PROJECTION_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)


class WriteProjectionBase(ProjectionBase):
    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_write: Callable[..., Any] | None = cls.__dict__.get("write")
        if original_write is not None and not getattr(
            original_write, _PROJECTION_WRAPPED_KEY, False
        ):
            wrapped = _make_write_wrapper(original_write)
            setattr(cls, "write", wrapped)
            setattr(wrapped, _PROJECTION_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)


class WriteProjection(WriteProjectionBase):
    session: Session | None = Field(default=None)

    @abstractmethod
    def write(self, model: WriteModel) -> Any: ...


class ReadProjection(ReadProjectionBase):
    session: Session | None = Field(default=None)

    @abstractmethod
    def read(self, model: ReadModel) -> Any: ...


class Projection(ReadProjection, WriteProjection):
    @abstractmethod
    def read(self, model: ReadModel) -> Any: ...

    @abstractmethod
    def write(self, model: WriteModel) -> Any: ...


class AsyncReadProjection(ProjectionBase):
    session: Session | AsyncSession | None = Field(default=None)

    @abstractmethod
    async def read(self, model: ReadModel) -> Any: ...


class AsyncWriteProjection(ProjectionBase):
    session: Session | AsyncSession | None = Field(default=None)

    @abstractmethod
    async def write(self, model: WriteModel) -> Any: ...


class AsyncProjection(AsyncReadProjection, AsyncWriteProjection):
    @abstractmethod
    async def read(self, model: ReadModel) -> Any: ...

    @abstractmethod
    async def write(self, model: WriteModel) -> Any: ...
