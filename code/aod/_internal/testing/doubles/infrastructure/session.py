from __future__ import annotations

from typing import Any

from aod._internal.core.fields.fields import PrivateField
from aod._internal.infrastructure.session import AsyncSession, Session


class SpySession(Session):
    _execute_calls: list[object] = PrivateField(default_factory=list)
    _query_calls: list[object] = PrivateField(default_factory=list)
    _begin_calls: list[None] = PrivateField(default_factory=list)
    _commit_calls: list[None] = PrivateField(default_factory=list)
    _rollback_calls: list[None] = PrivateField(default_factory=list)
    _close_calls: list[None] = PrivateField(default_factory=list)
    _dirty: bool = PrivateField(default=False)
    _execute_result: Any = PrivateField(default=None)
    _query_result: Any = PrivateField(default=None)

    @property
    def execute_calls(self) -> list[object]:
        return list(self._execute_calls)

    @property
    def query_calls(self) -> list[object]:
        return list(self._query_calls)

    @property
    def begin_calls(self) -> list[None]:
        return list(self._begin_calls)

    @property
    def commit_calls(self) -> list[None]:
        return list(self._commit_calls)

    @property
    def rollback_calls(self) -> list[None]:
        return list(self._rollback_calls)

    @property
    def close_calls(self) -> list[None]:
        return list(self._close_calls)

    def execute(self, operation: object) -> object:
        self._execute_calls.append(operation)
        return self._execute_result

    def query(self, operation: object) -> object:
        self._query_calls.append(operation)
        return self._query_result

    def begin(self) -> None:
        self._begin_calls.append(None)

    def commit(self) -> None:
        self._commit_calls.append(None)

    def rollback(self) -> None:
        self._rollback_calls.append(None)

    def close(self) -> None:
        self._close_calls.append(None)

    def is_dirty(self) -> bool:
        return self._dirty


class SpyAsyncSession(AsyncSession):
    _execute_calls: list[object] = PrivateField(default_factory=list)
    _query_calls: list[object] = PrivateField(default_factory=list)
    _begin_calls: list[None] = PrivateField(default_factory=list)
    _commit_calls: list[None] = PrivateField(default_factory=list)
    _rollback_calls: list[None] = PrivateField(default_factory=list)
    _close_calls: list[None] = PrivateField(default_factory=list)
    _dirty: bool = PrivateField(default=False)
    _execute_result: Any = PrivateField(default=None)
    _query_result: Any = PrivateField(default=None)

    @property
    def execute_calls(self) -> list[object]:
        return list(self._execute_calls)

    @property
    def query_calls(self) -> list[object]:
        return list(self._query_calls)

    @property
    def begin_calls(self) -> list[None]:
        return list(self._begin_calls)

    @property
    def commit_calls(self) -> list[None]:
        return list(self._commit_calls)

    @property
    def rollback_calls(self) -> list[None]:
        return list(self._rollback_calls)

    @property
    def close_calls(self) -> list[None]:
        return list(self._close_calls)

    async def execute(self, operation: object) -> object:
        self._execute_calls.append(operation)
        return self._execute_result

    async def query(self, operation: object) -> object:
        self._query_calls.append(operation)
        return self._query_result

    async def begin(self) -> None:
        self._begin_calls.append(None)

    async def commit(self) -> None:
        self._commit_calls.append(None)

    async def rollback(self) -> None:
        self._rollback_calls.append(None)

    async def close(self) -> None:
        self._close_calls.append(None)

    def is_dirty(self) -> bool:
        return self._dirty
