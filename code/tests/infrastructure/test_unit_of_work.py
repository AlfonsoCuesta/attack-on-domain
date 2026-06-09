from __future__ import annotations

from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.infrastructure.unit_of_work import AsyncUnitOfWork, UnitOfWork
from aod.domain import PrivateField


class _DirtySession(Session):
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)

    def is_dirty(self) -> bool:
        return True

    def execute(self, operation: object) -> object:
        return operation

    def query(self, operation: object) -> object:
        return operation

    def begin(self) -> None:
        pass

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        self._rolled_back = True

    def close(self) -> None:
        pass


class _CleanSession(Session):
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


class _DirtyAsyncSession(AsyncSession):
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)

    def is_dirty(self) -> bool:
        return True

    async def execute(self, operation: object) -> object:
        return operation

    async def query(self, operation: object) -> object:
        return operation

    async def begin(self) -> None:
        pass

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        self._rolled_back = True

    async def close(self) -> None:
        pass


class _CleanAsyncSession(AsyncSession):
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


class TestUnitOfWork:
    def test_commit_dirty_session(self) -> None:
        session = _DirtySession()
        uow = UnitOfWork(sessions={session})
        uow.commit()
        assert session._committed

    def test_commit_skips_clean_session(self) -> None:
        session = _CleanSession()
        uow = UnitOfWork(sessions={session})
        uow.commit()

    def test_rollback_dirty_session(self) -> None:
        session = _DirtySession()
        uow = UnitOfWork(sessions={session})
        uow.rollback()
        assert session._rolled_back

    def test_rollback_skips_clean_session(self) -> None:
        session = _CleanSession()
        uow = UnitOfWork(sessions={session})
        uow.rollback()

    def test_commit_multiple_sessions(self) -> None:
        s1 = _DirtySession()
        s2 = _DirtySession()
        uow = UnitOfWork(sessions={s1, s2})
        uow.commit()
        assert s1._committed
        assert s2._committed

    def test_rollback_multiple_sessions(self) -> None:
        s1 = _DirtySession()
        s2 = _DirtySession()
        uow = UnitOfWork(sessions={s1, s2})
        uow.rollback()
        assert s1._rolled_back
        assert s2._rolled_back


class TestAsyncUnitOfWork:
    async def test_commit_dirty_session(self) -> None:
        session = _DirtyAsyncSession()
        uow = AsyncUnitOfWork(sessions={session})
        await uow.commit()
        assert session._committed

    async def test_commit_skips_clean_session(self) -> None:
        session = _CleanAsyncSession()
        uow = AsyncUnitOfWork(sessions={session})
        await uow.commit()

    async def test_rollback_dirty_session(self) -> None:
        session = _DirtyAsyncSession()
        uow = AsyncUnitOfWork(sessions={session})
        await uow.rollback()
        assert session._rolled_back

    async def test_rollback_skips_clean_session(self) -> None:
        session = _CleanAsyncSession()
        uow = AsyncUnitOfWork(sessions={session})
        await uow.rollback()

    async def test_commit_sync_session(self) -> None:
        session = _DirtySession()
        uow = AsyncUnitOfWork(sessions={session})
        await uow.commit()
        assert session._committed

    async def test_rollback_sync_session(self) -> None:
        session = _DirtySession()
        uow = AsyncUnitOfWork(sessions={session})
        await uow.rollback()
        assert session._rolled_back

    async def test_commit_multiple_sessions(self) -> None:
        s1 = _DirtyAsyncSession()
        s2 = _DirtyAsyncSession()
        uow = AsyncUnitOfWork(sessions={s1, s2})
        await uow.commit()
        assert s1._committed
        assert s2._committed

    async def test_rollback_multiple_sessions(self) -> None:
        s1 = _DirtyAsyncSession()
        s2 = _DirtyAsyncSession()
        uow = AsyncUnitOfWork(sessions={s1, s2})
        await uow.rollback()
        assert s1._rolled_back
        assert s2._rolled_back
