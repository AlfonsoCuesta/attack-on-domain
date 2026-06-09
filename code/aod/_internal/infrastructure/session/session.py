from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, cast

from aod._internal.application.port import Port
from aod._internal.core.application_exception import CommitOutsideUnitOfWorkError
from aod._internal.infrastructure.commit_context import _CommitContext


def check_commit_context(fn) -> Callable[..., None]:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _CommitContext.get(False):
            raise CommitOutsideUnitOfWorkError()
        return fn(*args, **kwargs)

    return cast(Callable[..., None], wrapper)


def check_async_commit_context(fn) -> Callable[..., Coroutine[Any, Any, None]]:
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        if not _CommitContext.get(False):
            raise CommitOutsideUnitOfWorkError()
        return await fn(*args, **kwargs)

    return cast(Callable[..., Coroutine[Any, Any, None]], wrapper)


class Session(Port):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.commit: Callable[..., None] = check_commit_context(cls.commit)

    @abstractmethod
    def execute(self, operation: object) -> object: ...

    @abstractmethod
    def query(self, operation: object) -> object: ...

    @abstractmethod
    def begin(self) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def is_dirty(self) -> bool: ...


class AsyncSession(Port):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.commit: Callable[..., Coroutine[Any, Any, None]] = check_async_commit_context(
            cls.commit
        )

    @abstractmethod
    async def execute(self, operation: object) -> object: ...

    @abstractmethod
    async def query(self, operation: object) -> object: ...

    @abstractmethod
    async def begin(self) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    def is_dirty(self) -> bool: ...
