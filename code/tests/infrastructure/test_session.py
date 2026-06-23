from __future__ import annotations

import pytest
from aod._internal.core.application_exception import CommitOutsideUnitOfWorkError
from aod._internal.infrastructure.commit_context import _CommitContext
from aod._internal.infrastructure.session import AsyncSession, Session


class ConcreteSession(Session):
    def is_dirty(self) -> bool:
        return False

    def execute(self, operation: object) -> object:
        return operation

    def query(self, operation: object) -> object:
        return operation

    def begin(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


class ConcreteAsyncSession(AsyncSession):
    def is_dirty(self) -> bool:
        return False

    async def execute(self, operation: object) -> object:
        return operation

    async def query(self, operation: object) -> object:
        return operation

    async def begin(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass


class TestSession:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            Session()

    def test_concrete_session_works(self) -> None:
        s = ConcreteSession()
        assert s.execute("op") == "op"
        assert s.query("q") == "q"

    def test_lifecycle_methods(self) -> None:
        s = ConcreteSession()
        s.begin()
        token = _CommitContext.set(True)
        try:
            s.commit()
        finally:
            _CommitContext.reset(token)
        s.rollback()
        s.close()

    def test_commit_outside_uow_raises(self) -> None:
        s = ConcreteSession()
        with pytest.raises(CommitOutsideUnitOfWorkError):
            s.commit()


class TestAsyncSession:
    async def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            AsyncSession()

    async def test_concrete_async_session_works(self) -> None:
        s = ConcreteAsyncSession()
        result = await s.execute("op")
        assert result == "op"
        result = await s.query("q")
        assert result == "q"

    async def test_lifecycle_methods(self) -> None:
        s = ConcreteAsyncSession()
        await s.begin()
        token = _CommitContext.set(True)
        try:
            await s.commit()
        finally:
            _CommitContext.reset(token)
        await s.rollback()
        await s.close()

    async def test_commit_outside_uow_raises(self) -> None:
        s = ConcreteAsyncSession()
        with pytest.raises(CommitOutsideUnitOfWorkError):
            await s.commit()
