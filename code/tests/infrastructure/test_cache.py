from __future__ import annotations

from typing import Any

import pytest
from aod._internal.application.cache.cache import AsyncCache, Cache, _CacheEntry
from aod._internal.application.cache.cache_key import CacheInvalidation
from aod._internal.application.cache.cache_key_contracts import (
    ContractCacheInvalidation,
    ContractCacheKey,
)
from aod._internal.application.cache.cache_key_operations import OperationCacheKey
from aod._internal.application.cache.cache_manager import (
    CacheContext,
    CacheManager,
    get_cache_context,
)
from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler import (
    AsyncCommandPort,
    AsyncQueryPort,
    CommandPort,
    QueryPort,
)
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.domain.entity import RootEntity
from aod._internal.infrastructure.handlers.handlers import (
    AsyncCommandHandler,
    AsyncQueryHandler,
    CommandHandler,
    QueryHandler,
)
from aod._internal.infrastructure.session import Session


class User(RootEntity):
    id: int = Field(id=True)
    name: str


class _FakeOp(BaseOperation):
    def run(self) -> None:
        return None


_op = _FakeOp()


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


class TestCacheInvalidation:
    def test_creates_invalidation(self) -> None:
        inv = ContractCacheInvalidation(target_type=CreateUser, key_fn=lambda c: f"user:{c.name}")
        assert inv.target_type is CreateUser
        assert inv.key_fn(CreateUser(name="Alice")) == "user:Alice"

    def test_is_frozen(self) -> None:
        inv = ContractCacheInvalidation(target_type=CreateUser, key_fn=lambda c: "key")
        assert inv.target_type is CreateUser
        assert inv.key_fn(CreateUser(name="Alice")) == "key"


class TestCacheKey:
    def test_extracts_query_type_from_key(self) -> None:
        class UserCacheKey(ContractCacheKey[GetUser]):
            def key(self, query: GetUser) -> str:
                return f"user:{query.user_id}"

            def invalidate(self) -> list[CacheInvalidation]:
                return [
                    ContractCacheInvalidation(
                        target_type=CreateUser, key_fn=lambda c: f"user:{c.name}"
                    ),
                    ContractCacheInvalidation(
                        target_type=DeleteUser, key_fn=lambda c: f"user:{c.user_id}"
                    ),
                ]

        assert UserCacheKey.get_type() is GetUser
        assert UserCacheKey().get_command_types() == {CreateUser, DeleteUser}

    def test_extracts_invalidation_key_fns(self) -> None:
        class UserCacheKey(ContractCacheKey[GetUser]):
            def key(self, query: GetUser) -> str:
                return f"user:{query.user_id}"

            def invalidate(self) -> list[CacheInvalidation]:
                return [
                    ContractCacheInvalidation(
                        target_type=CreateUser, key_fn=lambda c: f"created:{c.name}"
                    ),
                ]

        fn = UserCacheKey().get_invalidation_key_fn(CreateUser)
        assert fn is not None
        assert fn(CreateUser(name="Alice")) == "created:Alice"

    def test_get_invalidation_returns_none_for_unknown_command(self) -> None:
        class UserCacheKey(ContractCacheKey[GetUser]):
            def key(self, query: GetUser) -> str:
                return f"user:{query.user_id}"

            def invalidate(self) -> list[CacheInvalidation]:
                return []

        assert UserCacheKey().get_invalidation_key_fn(CreateUser) is None


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


def _make_user_key() -> ContractCacheKey:
    class UserCacheKey(ContractCacheKey[GetUser]):
        def key(self, query: GetUser) -> str:
            return f"user:{query.user_id}"

        def invalidate(self) -> list[CacheInvalidation]:
            return [
                ContractCacheInvalidation(
                    target_type=CreateUser, key_fn=lambda c: f"user:{c.name}"
                ),
                ContractCacheInvalidation(
                    target_type=DeleteUser, key_fn=lambda c: f"user:{c.user_id}"
                ),
            ]

    return UserCacheKey()


def _make_user_op_key() -> OperationCacheKey:
    class GetUserOpKey(OperationCacheKey[UseCase]):
        def key(self, op: UseCase) -> str:
            return "user:op"

        def invalidate(self) -> list[CacheInvalidation]:
            return [
                ContractCacheInvalidation(
                    target_type=CreateUser, key_fn=lambda c: f"user:{c.name}"
                ),
            ]

    return GetUserOpKey()


class TestResolveTtlReturnsNone:
    def test_no_matching_key(self) -> None:
        class OtherQuery(Query[User, User | None]):
            other_id: int

        cache = ConcreteCache(keys=[_make_user_key()])
        assert cache._resolve_ttl(OtherQuery(other_id=1)) is None


class TestCacheKeyTypeError:
    def test_contract_cache_key_requires_generic_param(self) -> None:
        with pytest.raises(TypeError, match="must be parameterized with a Query type"):

            class _(ContractCacheKey):  # type: ignore[type-arg]
                def key(self, query: str) -> str:
                    return query

                def invalidate(self) -> list[CacheInvalidation]:
                    return []


class TestAsyncCacheConcrete:
    async def test_async_get(self) -> None:
        cache = ConcreteAsyncCache(keys=[_make_user_key()])
        await cache.set("user:42", User(id=42, name="async"))
        result = await cache._get(GetUser(user_id=42))
        assert result is not None
        assert result.name == "async"

    async def test_async_flush_with_set(self) -> None:
        cache = ConcreteAsyncCache(keys=[_make_user_key()])
        cache._set(GetUser(user_id=1), User(id=1, name="x"))
        assert len(cache._to_set) == 1
        await cache._flush()
        assert len(cache._to_set) == 0
        stored = await cache.get("user:1")
        assert stored.name == "x"  # ty: ignore[unresolved-attribute]

    async def test_async_flush_with_delete(self) -> None:
        class DelKey(ContractCacheKey[GetUser]):
            ttl = 60.0

            def key(self, query: GetUser) -> str:
                return f"user:{query.user_id}"

            def invalidate(self) -> list[CacheInvalidation]:
                return [
                    ContractCacheInvalidation(
                        target_type=DeleteUser, key_fn=lambda c: f"user:{c.user_id}"
                    )
                ]

        cache = ConcreteAsyncCache(keys=[DelKey()])
        await cache.set("user:1", User(id=1, name="x"))
        cache._delete(DeleteUser(user_id=1))
        assert len(cache._to_delete) == 1
        await cache._flush()
        assert len(cache._to_delete) == 0
        assert await cache.get("user:1") is None

    async def test_async_flush_empty(self) -> None:
        cache = ConcreteAsyncCache(keys=[_make_user_key()])
        await cache._flush()
        assert len(cache._to_set) == 0
        assert len(cache._to_delete) == 0


class TestNullCache:
    def test_null_cache_noops(self) -> None:
        from aod._internal.application.cache.null_cache import NullCache

        nc = NullCache()
        nc._set(GetUser(user_id=1), User(id=1, name="x"))
        nc._delete(CreateUser(name="Alice"))
        nc._flush()
        assert nc._get(GetUser(user_id=1)) is None

    def test_null_cache_get_noop(self) -> None:
        from aod._internal.application.cache.null_cache import NullCache

        nc = NullCache()
        assert nc.get("any") is None

    def test_null_cache_set_delete_noop(self) -> None:
        from aod._internal.application.cache.null_cache import NullCache

        nc = NullCache()
        nc.set("k", "v")
        nc.delete("k")


class TestCacheContext:
    def test_get_for_returns_cache_when_key_matches(self) -> None:
        cache = ConcreteCache(keys=[_make_user_key()])
        ctx = CacheContext([cache])
        result = ctx.get_for(GetUser(user_id=1))
        assert result is cache

    def test_get_for_returns_none_when_no_match(self) -> None:
        cache = ConcreteCache(keys=[_make_user_key()])
        ctx = CacheContext([cache])

        class OtherQuery(Query[User, User | None]):
            other_id: int

        result = ctx.get_for(OtherQuery(other_id=1))
        assert result is None

    def test_get_for_returns_none_when_no_caches(self) -> None:
        ctx = CacheContext()
        assert ctx.get_for(GetUser(user_id=1)) is None

    def test_get_for_matches_operation_cache_key(self) -> None:
        class _ConcreteUC(UseCase):
            def run(self) -> None: ...

        cache = ConcreteCache(keys=[_make_user_op_key()])
        ctx = CacheContext([cache])
        uc = _ConcreteUC()
        result = ctx.get_for(uc)
        assert result is cache

    def test_get_delegates_to_cache(self) -> None:
        cache = ConcreteCache(keys=[_make_user_key()])
        cache.set("user:42", User(id=42, name="cached"))
        ctx = CacheContext([cache])
        result = ctx.get(GetUser(user_id=42))
        assert result is not None
        assert result.name == "cached"

    def test_get_returns_none_when_cache_misses(self) -> None:
        cache = ConcreteCache(keys=[_make_user_key()])
        ctx = CacheContext([cache])
        result = ctx.get(GetUser(user_id=99))
        assert result is None

    def test_set_delegates_to_cache(self) -> None:
        cache = ConcreteCache(keys=[_make_user_key()])
        ctx = CacheContext([cache])
        ctx.set(GetUser(user_id=1), User(id=1, name="val"))
        assert len(cache._to_set) == 1

    def test_delete_calls_on_all_caches(self) -> None:
        cache1 = ConcreteCache(keys=[_make_user_key()])
        cache2 = ConcreteCache(keys=[_make_user_key()])
        ctx = CacheContext([cache1, cache2])
        ctx.delete(CreateUser(name="Alice"))
        assert len(cache1._to_delete) == 1
        assert len(cache2._to_delete) == 1

    def test_delete_skips_when_no_caches(self) -> None:
        ctx = CacheContext()
        ctx.delete(CreateUser(name="Alice"))

    def test_flush_calls_on_all_caches(self) -> None:
        cache1 = ConcreteCache(keys=[_make_user_key()])
        cache2 = ConcreteCache(keys=[_make_user_key()])
        cache1._set(GetUser(user_id=1), User(id=1, name="x"))
        cache2._set(GetUser(user_id=2), User(id=2, name="y"))
        ctx = CacheContext([cache1, cache2])
        ctx.flush()
        assert len(cache1._to_set) == 0
        assert len(cache2._to_set) == 0

    def test_discard_clears_pending_ops(self) -> None:
        cache = ConcreteCache(keys=[_make_user_key()])
        cache._set(GetUser(user_id=1), User(id=1, name="x"))
        cache._delete(CreateUser(name="Alice"))
        ctx = CacheContext([cache])
        ctx.discard()
        assert len(cache._to_set) == 0
        assert len(cache._to_delete) == 0


class TestCacheManager:
    def test_get_cache_context_returns_empty_outside_block(self) -> None:
        ctx = get_cache_context()
        assert ctx is not None
        assert ctx.get_for(_op) is None

    def test_cache_context_set_and_cleared(self) -> None:
        cache = ConcreteCache(keys=[_make_user_key()])
        with CacheManager(cache):
            ctx = get_cache_context()
            assert ctx is not None
        ctx = get_cache_context()
        assert ctx is not None
        assert ctx.get_for(_op) is None

    def test_cache_context_with_multiple_caches(self) -> None:
        cache1 = ConcreteCache(keys=[_make_user_key()])
        cache2 = ConcreteCache(keys=[_make_user_key()])
        with CacheManager(cache1, cache2):
            ctx = get_cache_context()
            assert ctx is not None

    def test_duplicate_caches_deduplicated(self) -> None:
        cache = ConcreteCache(keys=[_make_user_key()])
        mgr = CacheManager(cache, cache)
        assert len(mgr._caches) == 1

    def test_context_get_works_inside_block(self) -> None:
        cache = ConcreteCache(keys=[_make_user_key()])
        cache.set("user:1", User(id=1, name="cached"))
        with CacheManager(cache):
            ctx = get_cache_context()
            assert ctx is not None
            result = ctx.get(GetUser(user_id=1))
            assert result is not None
            assert result.name == "cached"

    def test_context_set_and_flush_inside_block(self) -> None:
        cache = ConcreteCache(keys=[_make_user_key()])
        with CacheManager(cache):
            ctx = get_cache_context()
            assert ctx is not None
            ctx.set(GetUser(user_id=1), User(id=1, name="val"))
            ctx.flush()
            stored = cache.get("user:1")
            assert stored is not None
            assert stored.name == "val"  # ty: ignore[unresolved-attribute]

    def test_context_delete_inside_block(self) -> None:
        cache = ConcreteCache(keys=[_make_user_key()])
        cache.set("user:Alice", User(id=1, name="old"))
        with CacheManager(cache):
            ctx = get_cache_context()
            assert ctx is not None
            ctx.delete(CreateUser(name="Alice"))
            ctx.flush()
            assert cache.get("user:Alice") is None


class TestUseCaseWithCache:
    def test_read_through_hit(self) -> None:
        class GetUserUC(UseCase):
            get_user: QueryPort[GetUser]

            def run(self, user_id: int) -> User | None:
                return self.get_user.handle(GetUser(user_id=user_id))

        class GetUserHandlerLocal(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> User | None:
                return User(id=query.user_id, name="from-db")

        cache = ConcreteCache(keys=[_make_user_key()])
        cache.set("user:1", User(id=1, name="cached"))

        uc = GetUserUC(get_user=GetUserHandlerLocal())
        with CacheManager(cache):
            result = uc.run(user_id=1)
        assert result is not None
        assert result.name == "cached"

    def test_command_invalidates_cache(self) -> None:
        class CreateUserUC(UseCase):
            create_user: CommandPort[CreateUser]

            def run(self, name: str) -> User:
                return self.create_user.handle(CreateUser(name=name))

        class CreateUserHandlerLocal(CommandHandler[CreateUser]):
            def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        cache = ConcreteCache(keys=[_make_user_key()])
        cache.set("user:Alice", User(id=1, name="old"))

        uc = CreateUserUC(create_user=CreateUserHandlerLocal())
        with CacheManager(cache):
            result = uc.run(name="Alice")
        assert result.name == "Alice"
        assert cache.get("user:Alice") is None


class TestAsyncUseCaseWithCache:
    async def test_read_through_hit(self) -> None:
        class GetUserUC(AsyncUseCase):
            get_user: AsyncQueryPort[GetUser]

            async def run(self, user_id: int) -> User | None:
                return await self.get_user.handle(GetUser(user_id=user_id))

        class GetUserHandlerLocal(AsyncQueryHandler[GetUser]):
            async def handle(self, query: GetUser) -> User | None:
                return User(id=query.user_id, name="from-db")

        cache = ConcreteAsyncCache(keys=[_make_user_key()])
        await cache.set("user:1", User(id=1, name="cached"))

        uc = GetUserUC(get_user=GetUserHandlerLocal())
        with CacheManager(cache):
            result = await uc.run(user_id=1)
        assert result is not None
        assert result.name == "cached"

    async def test_read_through_miss_stores_result(self) -> None:
        class GetUserUC(AsyncUseCase):
            get_user: AsyncQueryPort[GetUser]

            async def run(self, user_id: int) -> User | None:
                return await self.get_user.handle(GetUser(user_id=user_id))

        class GetUserHandlerLocal(AsyncQueryHandler[GetUser]):
            async def handle(self, query: GetUser) -> User | None:
                return User(id=query.user_id, name="from-db")

        cache = ConcreteAsyncCache(keys=[_make_user_key()])

        uc = GetUserUC(get_user=GetUserHandlerLocal())
        with CacheManager(cache):
            result = await uc.run(user_id=2)
        assert result is not None
        assert result.name == "from-db"
        stored = await cache.get("user:2")
        assert stored is not None
        assert stored.name == "from-db"  # ty: ignore[unresolved-attribute]

    async def test_command_invalidates_cache(self) -> None:
        class CreateUserUC(AsyncUseCase):
            create_user: AsyncCommandPort[CreateUser]

            async def run(self, name: str) -> User:
                return await self.create_user.handle(CreateUser(name=name))

        class CreateUserHandlerLocal(AsyncCommandHandler[CreateUser]):
            async def handle(self, command: CreateUser) -> User:
                return User(id=1, name=command.name)

        cache = ConcreteAsyncCache(keys=[_make_user_key()])
        await cache.set("user:Alice", User(id=1, name="old"))

        uc = CreateUserUC(create_user=CreateUserHandlerLocal())
        with CacheManager(cache):
            result = await uc.run(name="Alice")
        assert result.name == "Alice"
        assert await cache.get("user:Alice") is None
