from __future__ import annotations

from typing import Any

from aod._internal.application.cache.cache import Cache
from aod._internal.application.cache.cache_key import CacheKey, Invalidation
from aod._internal.application.contracts import Command, Query
from aod._internal.application.unit_of_work import AsyncUnitOfWork, UnitOfWork
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.domain.entity import RootEntity
from aod._internal.infrastructure.handlers.handlers import CommandHandler, QueryHandler
from aod._internal.infrastructure.session import AsyncSession, Session


class User(RootEntity):
    id: int = Field(id=True)
    name: str


class GetUser(Query[User, User | None]):
    user_id: int


class CreateUser(Command[User, User]):
    name: str


class _SyncSession(Session):
    def execute(self, operation: object) -> object: ...
    def query(self, operation: object) -> object: ...
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def is_dirty(self) -> bool:
        return False


class ConcreteCache(Cache):
    _stored: dict[str, Any] = PrivateField(default_factory=dict)

    def get(self, key: str) -> object:
        return self._stored.get(key)

    def set(self, key: str, value: object, ttl: float | None = None) -> None:
        self._stored[key] = value

    def delete(self, key: str) -> None:
        self._stored.pop(key, None)


def _make_user_key() -> CacheKey:
    class UserCacheKey(CacheKey[GetUser]):
        def key(self, query: GetUser) -> str:
            return f"user:{query.user_id}"

        def invalidate(self) -> list[Invalidation]:
            return [
                Invalidation(CreateUser, lambda c: f"user:{c.name}"),
            ]

    return UserCacheKey()


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


class TestUowAddHandler:
    def test_add_handler_collects_sessions(self) -> None:
        class Handler(QueryHandler[GetUser]):
            session: _SyncSession

            def handle(self, query: GetUser) -> User | None:
                return None

        session = _SyncSession()
        handler = Handler(session=session)
        uow = UnitOfWork()
        uow.add_handler(handler)
        assert session in uow.sessions

    def test_add_handler_collects_caches(self) -> None:
        class Handler(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return None

        cache = ConcreteCache(keys=[_make_user_key()])
        handler = Handler()
        handler.add_cache(cache)
        uow = UnitOfWork()
        uow.add_handler(handler)
        assert cache in uow.caches

    def test_add_handler_dedup_caches(self) -> None:
        class Handler1(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return None

        class Handler2(CommandHandler[CreateUser]):
            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        cache = ConcreteCache(keys=[_make_user_key()])
        h1 = Handler1()
        h1.add_cache(cache)
        h2 = Handler2()
        h2.add_cache(cache)

        uow = UnitOfWork()
        uow.add_handler(h1)
        uow.add_handler(h2)
        assert len(uow.caches) == 1

    def test_uow_commit_flushes_caches(self) -> None:
        class Handler(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return None

        cache = ConcreteCache(keys=[_make_user_key()])
        cache._set(GetUser(user_id=1), User(id=1, name="x"))
        handler = Handler()
        handler.add_cache(cache)
        uow = UnitOfWork()
        uow.add_handler(handler)
        assert len(cache._to_set) == 1
        uow.commit()
        assert len(cache._to_set) == 0
        assert cache.get("user:1").name == "x"  # ty: ignore[unresolved-attribute]
