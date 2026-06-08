from __future__ import annotations

import pytest
from aod._internal.infrastructure.session import AsyncSession, Session


class ConcreteSession(Session):
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
        s.commit()
        s.rollback()
        s.close()


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
        await s.commit()
        await s.rollback()
        await s.close()