from __future__ import annotations

from typing import Any

import pytest
from aod._internal.application.cache.cache_key import CacheKey, Invalidation
from aod._internal.application.contracts import Command, Query
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.domain.entity import RootEntity
from aod._internal.application.cache.cache import AsyncCache, Cache, _CacheEntry
from aod._internal.infrastructure.handlers.handlers import (
    AsyncCommandHandler,
    AsyncQueryHandler,
    CommandHandler,
    QueryHandler,
)
from aod._internal.infrastructure.session import Session
from aod._internal.infrastructure.unit_of_work import UnitOfWork as InfraUnitOfWork


class User(RootEntity):
    id: int = Field(id=True)
    name: str


class GetUser(Query[User, User | None]):
    user_id: int


class CreateUser(Command[User, User]):
    name: str


class DeleteUser(Command[User, None]):
    user_id: int


class UpdateUser(Command[User, User]):
    user_id: int
    name: str


class ConcreteCache(Cache):
    _stored: dict[str, Any] = PrivateField(default_factory=dict)

    def get(self, key: str, default: Any = None) -> object:
        return self._stored.get(key)

    def set(self, key: str, value: object, ttl: float | None = None) -> None:
        self._stored[key] = value

    def delete(self, key: str) -> None:
        self._stored.pop(key, None)


class ConcreteAsyncCache(AsyncCache):
    _stored: dict[str, Any] = PrivateField(default_factory=dict)

    async def get(self, key: str, default: Any = None) -> object:
        return self._stored.get(key)

    async def set(self, key: str, value: object, ttl: float | None = None) -> None:
        self._stored[key] = value

    async def delete(self, key: str) -> None:
        self._stored.pop(key, None)


class _SyncSession(Session):
    def execute(self, operation: object) -> object: ...
    def query(self, operation: object) -> object: ...
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def is_dirty(self) -> bool:
        return False


class TestCacheEntry:
    def test_default_ttl_is_none(self) -> None:
        item = _CacheEntry(key="k", value="v")
        assert item.key == "k"
        assert item.value == "v"
        assert item.ttl is None

    def test_with_ttl(self) -> None:
        item = _CacheEntry(key="k", value="v", ttl=60.0)
        assert item.ttl == 60.0


class TestCache:
    def test_set_batches(self) -> None:
        c = ConcreteCache(keys=[_make_user_key()])
        c._set(GetUser(user_id=1), User(id=1, name="x"))
        assert len(c._to_set) == 1
        assert c._to_set[0].key == "user:1"

    def test_delete_batches(self) -> None:
        c = ConcreteCache(keys=[_make_user_key()])
        c._delete(CreateUser(name="Alice"))
        assert len(c._to_delete) == 1
        assert c._to_delete[0] == "user:Alice"

    def test_flush_with_both(self) -> None:
        c = ConcreteCache(keys=[_make_user_key()])
        c._set(GetUser(user_id=1), User(id=1, name="x"))
        c._set(GetUser(user_id=2), User(id=2, name="y"))
        c._delete(CreateUser(name="Alice"))
        c._flush()
        assert len(c._to_set) == 0
        assert len(c._to_delete) == 0

    def test_flush_empty(self) -> None:
        c = ConcreteCache(keys=[_make_user_key()])
        c._flush()
        assert len(c._to_set) == 0
        assert len(c._to_delete) == 0

    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            Cache()


class TestAsyncCache:
    async def test_set_batches(self) -> None:
        c = ConcreteAsyncCache(keys=[_make_user_key()])
        c._set(GetUser(user_id=1), User(id=1, name="x"))
        assert len(c._to_set) == 1

    async def test_delete_batches(self) -> None:
        c = ConcreteAsyncCache(keys=[_make_user_key()])
        c._delete(CreateUser(name="Alice"))
        assert len(c._to_delete) == 1

    async def test_flush_with_both(self) -> None:
        c = ConcreteAsyncCache(keys=[_make_user_key()])
        c._set(GetUser(user_id=1), User(id=1, name="x"))
        c._set(GetUser(user_id=2), User(id=2, name="y"))
        c._delete(CreateUser(name="Alice"))
        await c._flush()
        assert len(c._to_set) == 0
        assert len(c._to_delete) == 0

    async def test_flush_empty(self) -> None:
        c = ConcreteAsyncCache(keys=[_make_user_key()])
        await c._flush()
        assert len(c._to_set) == 0
        assert len(c._to_delete) == 0

    async def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            AsyncCache()


class TestInvalidation:
    def test_creates_invalidation(self) -> None:
        inv = Invalidation(CreateUser, lambda c: f"user:{c.name}")
        assert inv.command_type is CreateUser
        assert inv.key_fn(CreateUser(name="Alice")) == "user:Alice"

    def test_is_frozen(self) -> None:
        inv = Invalidation(CreateUser, lambda c: "key")
        assert inv.command_type is CreateUser
        assert inv.key_fn(CreateUser(name="Alice")) == "key"


class TestCacheKey:
    def test_extracts_query_type_from_key(self) -> None:
        class UserCacheKey(CacheKey[GetUser]):
            def key(self, query: GetUser) -> str:
                return f"user:{query.user_id}"

            def invalidate(self) -> list[Invalidation]:
                return [
                    Invalidation(CreateUser, lambda c: f"user:{c.name}"),
                    Invalidation(DeleteUser, lambda c: f"user:{c.user_id}"),
                ]

        assert UserCacheKey.get_query_type() is GetUser
        assert UserCacheKey.get_command_types() == {CreateUser, DeleteUser}

    def test_extracts_invalidation_key_fns(self) -> None:
        class UserCacheKey(CacheKey[GetUser]):
            def key(self, query: GetUser) -> str:
                return f"user:{query.user_id}"

            def invalidate(self) -> list[Invalidation]:
                return [
                    Invalidation(CreateUser, lambda c: f"created:{c.name}"),
                ]

        fn = UserCacheKey.get_invalidation_key_fn(CreateUser)
        assert fn is not None
        assert fn(CreateUser(name="Alice")) == "created:Alice"

    def test_get_invalidation_returns_none_for_unknown_command(self) -> None:
        class UserCacheKey(CacheKey[GetUser]):
            def key(self, query: GetUser) -> str:
                return f"user:{query.user_id}"

            def invalidate(self) -> list[Invalidation]:
                return []

        assert UserCacheKey.get_invalidation_key_fn(CreateUser) is None


class TestCacheWithKeys:
    def test_get_resolves_and_returns(self) -> None:
        key1 = _make_user_key()
        cache = ConcreteCache(keys=[key1])
        cache.set("user:42", User(id=42, name="cached"))
        result = cache._get(GetUser(user_id=42))
        assert result is not None
        assert result.name == "cached"

    def test_get_raises_for_unregistered_query(self) -> None:
        class GetOrder(Query[User, User | None]):
            order_id: int

        key1 = _make_user_key()
        cache = ConcreteCache(keys=[key1])

        with pytest.raises(RuntimeError, match="No cache key registered"):
            cache._get(GetOrder(order_id=1))

    def test_delete_batches_keys(self) -> None:
        key1 = _make_user_key()
        cache = ConcreteCache(keys=[key1])
        cache._delete(CreateUser(name="Alice"))
        assert cache._to_delete == ["user:Alice"]

    def test_delete_empty_for_unregistered_command(self) -> None:
        key1 = _make_user_key()
        cache = ConcreteCache(keys=[key1])
        cache._delete(UpdateUser(user_id=1, name="Bob"))
        assert cache._to_delete == []


class TestHandlerAddCacheQuery:
    def test_add_cache_read_through_hit(self) -> None:
        class GetUserHandler(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:  # type: ignore[empty-body]
                return User(id=query.user_id, name="from-db")

        cache = ConcreteCache(keys=[_make_user_key()])
        cache.set("user:1", User(id=1, name="cached"))

        handler = GetUserHandler()
        handler.add_cache(cache)

        result = handler.handle(GetUser(user_id=1))
        assert result is not None
        assert result.name == "cached"

    def test_add_cache_read_through_miss(self) -> None:
        class GetUserHandler(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return User(id=query.user_id, name="from-db")

        cache = ConcreteCache(keys=[_make_user_key()])

        handler = GetUserHandler()
        handler.add_cache(cache)

        result = handler.handle(GetUser(user_id=99))
        assert result is not None
        assert result.name == "from-db"
        assert cache.get("user:99") is None
        cache._flush()
        cached = cache.get("user:99")
        assert cached is not None
        assert cached.name == "from-db"  # ty: ignore[unresolved-attribute]

    def test_add_cache_read_through_returns_none_not_cached(self) -> None:
        class GetUserHandler(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return None

        cache = ConcreteCache(keys=[_make_user_key()])

        handler = GetUserHandler()
        handler.add_cache(cache)

        result = handler.handle(GetUser(user_id=999))
        assert result is None

    def test_cannot_add_two_caches_to_query_handler(self) -> None:
        class GetUserHandler(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return None

        cache1 = ConcreteCache(keys=[_make_user_key()])
        cache2 = ConcreteCache(keys=[_make_user_key()])

        handler = GetUserHandler()
        handler.add_cache(cache1)
        with pytest.raises(ValueError, match="already has a cache"):
            handler.add_cache(cache2)

    def test_get_caches_returns_cache(self) -> None:
        class GetUserHandler(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return None

        cache = ConcreteCache(keys=[_make_user_key()])
        handler = GetUserHandler()
        handler.add_cache(cache)

        assert handler._get_caches() == [cache]

    def test_get_caches_empty_when_no_cache(self) -> None:
        class GetUserHandler(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return None

        handler = GetUserHandler()
        assert handler._get_caches() == []


class TestHandlerAddCacheCommand:
    def test_add_cache_invalidates_after_handle(self) -> None:
        class CreateUserHandler(CommandHandler[CreateUser]):
            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        cache = ConcreteCache(keys=[_make_user_key()])

        handler = CreateUserHandler()
        handler.add_cache(cache)

        handler.handle(CreateUser(name="Alice"))
        cache._flush()
        assert cache.get("user:Alice") is None

    def test_multiple_caches_on_command_handler(self) -> None:
        class UserListCacheKey(CacheKey[GetUser]):
            def key(self, query: GetUser) -> str:
                return "users:list"

            def invalidate(self) -> list[Invalidation]:
                return [Invalidation(CreateUser, lambda c: "users:list")]

        cache1 = ConcreteCache(keys=[_make_user_key()])
        cache2 = ConcreteCache(keys=[UserListCacheKey()])

        class CreateUserHandler(CommandHandler[CreateUser]):
            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        handler = CreateUserHandler()
        handler.add_cache(cache1)
        handler.add_cache(cache2)

        handler.handle(CreateUser(name="Alice"))
        assert len(cache1._to_delete) == 1
        assert len(cache2._to_delete) == 1

    def test_get_caches_returns_all(self) -> None:
        cache1 = ConcreteCache(keys=[_make_user_key()])
        cache2 = ConcreteCache(keys=[_make_user_key()])

        class CreateUserHandler(CommandHandler[CreateUser]):
            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        handler = CreateUserHandler()
        handler.add_cache(cache1)
        handler.add_cache(cache2)

        caches = handler._get_caches()
        assert len(caches) == 2
        assert cache1 in caches
        assert cache2 in caches


class TestHandlerGetSessions:
    def test_get_sessions_returns_session_fields(self) -> None:
        class HandlerWithSession(QueryHandler[GetUser]):
            session: _SyncSession

            def handle(self, query: GetUser) -> User | None:
                return None

        session = _SyncSession()
        handler = HandlerWithSession(session=session)
        sessions = handler._get_sessions()
        assert sessions == [session]

    def test_get_sessions_empty_when_no_session(self) -> None:
        class Handler(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return None

        handler = Handler()
        assert handler._get_sessions() == []


class TestUowAddHandler:
    def test_add_handler_collects_sessions(self) -> None:
        class Handler(QueryHandler[GetUser]):
            session: _SyncSession

            def handle(self, query: GetUser) -> User | None:
                return None

        session = _SyncSession()
        handler = Handler(session=session)
        uow = InfraUnitOfWork()
        uow.add_handler(handler)
        assert session in uow.sessions

    def test_add_handler_collects_caches(self) -> None:
        class Handler(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return None

        cache = ConcreteCache(keys=[_make_user_key()])
        handler = Handler()
        handler.add_cache(cache)
        uow = InfraUnitOfWork()
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

        uow = InfraUnitOfWork()
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
        uow = InfraUnitOfWork()
        uow.add_handler(handler)
        assert len(cache._to_set) == 1
        uow.commit()
        assert len(cache._to_set) == 0
        assert cache.get("user:1").name == "x"  # ty: ignore[unresolved-attribute]


class TestAsyncHandlerCache:
    async def test_async_query_read_through_hit(self) -> None:
        class GetUserHandler(AsyncQueryHandler[GetUser]):
            async def handle(self, query: GetUser) -> User | None:
                return User(id=query.user_id, name="from-db")

        cache = ConcreteCache(keys=[_make_user_key()])
        cache.set("user:1", User(id=1, name="cached"))

        handler = GetUserHandler()
        handler.add_cache(cache)
        result = await handler.handle(GetUser(user_id=1))
        assert result is not None
        assert result.name == "cached"

    async def test_async_query_read_through_miss(self) -> None:
        class GetUserHandler(AsyncQueryHandler[GetUser]):
            async def handle(self, query: GetUser) -> User | None:
                return User(id=query.user_id, name="from-db")

        cache = ConcreteCache(keys=[_make_user_key()])

        handler = GetUserHandler()
        handler.add_cache(cache)
        result = await handler.handle(GetUser(user_id=99))
        assert result is not None
        assert result.name == "from-db"
        cache._flush()
        cached = cache.get("user:99")
        assert cached is not None
        assert cached.name == "from-db"  # ty: ignore[unresolved-attribute]

    async def test_async_command_invalidates(self) -> None:
        class CreateUserHandler(AsyncCommandHandler[CreateUser]):
            async def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        cache = ConcreteCache(keys=[_make_user_key()])
        handler = CreateUserHandler()
        handler.add_cache(cache)
        await handler.handle(CreateUser(name="Alice"))
        assert len(cache._to_delete) == 1


def _make_user_key() -> CacheKey:
    class UserCacheKey(CacheKey[GetUser]):
        def key(self, query: GetUser) -> str:
            return f"user:{query.user_id}"

        def invalidate(self) -> list[Invalidation]:
            return [
                Invalidation(CreateUser, lambda c: f"user:{c.name}"),
                Invalidation(DeleteUser, lambda c: f"user:{c.user_id}"),
            ]

    return UserCacheKey()
