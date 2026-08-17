from __future__ import annotations

from abc import abstractmethod
from collections.abc import Coroutine
from functools import wraps
from typing import Any, Callable, cast

from aod._internal.application.port import Port
from aod._internal.core.application_exception import CommitOutsideUnitOfWorkError
from aod._internal.core.fields import PrivateField
from aod._internal.core.transaction_context import get_active_transaction
from aod._internal.infrastructure.commit_context import _CommitContext


def check_commit_context(fn: Callable[..., None]) -> Callable[..., None]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        if not _CommitContext.get(False):
            raise CommitOutsideUnitOfWorkError()
        fn(*args, **kwargs)

    return wrapper


def check_async_commit_context(
    fn: Callable[..., Coroutine[Any, Any, None]],
) -> Callable[..., Coroutine[Any, Any, None]]:
    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> None:
        if not _CommitContext.get(False):
            raise CommitOutsideUnitOfWorkError()
        await fn(*args, **kwargs)

    return cast(Callable[..., Coroutine[Any, Any, None]], wrapper)


class Session(Port):
    _is_begun: bool = PrivateField(default=False)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.commit: Callable[..., None] = check_commit_context(cls.commit)

    def _begin(self) -> None:
        transaction = get_active_transaction()
        if not self._is_begun:
            self.begin()
            object.__setattr__(self, "_is_begun", True)
        if transaction is not None:
            transaction.register_session(self)

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
    _is_begun: bool = PrivateField(default=False)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.commit: Callable[..., Coroutine[Any, Any, None]] = check_async_commit_context(
            cls.commit
        )

    async def _begin(self) -> None:
        transaction = get_active_transaction()
        if not self._is_begun:
            await self.begin()
            object.__setattr__(self, "_is_begun", True)
        if transaction is not None:
            transaction.register_session(self)

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
