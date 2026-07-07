from __future__ import annotations

from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.infrastructure.unit_of_work import AsyncUnitOfWork, UnitOfWork
from aod._internal.testing.doubles.infrastructure.session import session_stub


class TestUnitOfWorkBegin:
    def test_begin_calls_begin_on_all_sessions(self) -> None:
        s1 = session_stub(Session)()
        s2 = session_stub(Session)()
        uow = UnitOfWork(sessions={s1, s2})
        uow.begin()
        assert s1.begin.call_count == 1
        assert s2.begin.call_count == 1

    def test_begin_with_empty_sessions(self) -> None:
        uow = UnitOfWork(sessions=set())
        uow.begin()

    def test_begin_then_commit(self) -> None:
        s1 = session_stub(Session)()
        s1.is_dirty.return_value = True
        uow = UnitOfWork(sessions={s1})
        uow.begin()
        uow.commit()
        assert s1.begin.call_count == 1

    def test_begin_then_rollback_dirty(self) -> None:
        s1 = session_stub(Session)()
        s1.is_dirty.return_value = True
        uow = UnitOfWork(sessions={s1})
        uow.begin()
        uow.rollback()
        assert s1.begin.call_count == 1
        assert s1.rollback.call_count == 1


class TestAsyncUnitOfWorkBegin:
    async def test_begin_calls_begin_on_all_sessions(self) -> None:
        s1 = session_stub(AsyncSession)()
        s2 = session_stub(AsyncSession)()
        uow = AsyncUnitOfWork(sessions={s1, s2})
        await uow.begin()
        assert s1.begin.call_count == 1
        assert s2.begin.call_count == 1

    async def test_begin_with_empty_sessions(self) -> None:
        uow = AsyncUnitOfWork(sessions=set())
        await uow.begin()
