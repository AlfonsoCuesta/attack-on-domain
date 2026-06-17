from __future__ import annotations

from aod._internal.testing.doubles.application.cache import AsyncSpyCache, SpyCache


class TestSpyCache:
    def test_get_returns_none_for_missing_key(self) -> None:
        cache = SpyCache()
        assert cache.get("missing") is None

    def test_get_returns_set_value(self) -> None:
        cache = SpyCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_tracks_calls(self) -> None:
        cache = SpyCache()
        cache.get("a")
        cache.get("b")
        assert cache.get_calls == ["a", "b"]

    def test_set_stores_value(self) -> None:
        cache = SpyCache()
        cache.set("k", "v", ttl=60.0)
        assert cache.get("k") == "v"

    def test_set_tracks_calls(self) -> None:
        cache = SpyCache()
        cache.set("k", "v", ttl=60.0)
        assert cache.set_calls == [("k", "v", 60.0)]

    def test_set_without_ttl(self) -> None:
        cache = SpyCache()
        cache.set("k", "v")
        assert cache.set_calls == [("k", "v", None)]

    def test_delete_removes_value(self) -> None:
        cache = SpyCache()
        cache.set("k", "v")
        cache.delete("k")
        assert cache.get("k") is None

    def test_delete_tracks_calls(self) -> None:
        cache = SpyCache()
        cache.delete("k")
        assert cache.delete_calls == ["k"]

    def test_flush_tracks_calls(self) -> None:
        cache = SpyCache()
        cache.flush()
        assert cache.flush_calls == [None]

    def test_set_promise_tracks_calls(self) -> None:
        cache = SpyCache()
        cache.set_promise("k", "v", ttl=30.0)
        assert cache.set_promise_calls == [("k", "v", 30.0)]

    def test_set_promise_without_ttl(self) -> None:
        cache = SpyCache()
        cache.set_promise("k", "v")
        assert cache.set_promise_calls == [("k", "v", None)]

    def test_delete_promise_tracks_calls(self) -> None:
        cache = SpyCache()
        cache.delete_promise("k")
        assert cache.delete_promise_calls == ["k"]

    def test_get_calls_returns_copy(self) -> None:
        cache = SpyCache()
        cache.get("a")
        calls = cache.get_calls
        calls.append("b")
        assert cache.get_calls == ["a"]

    def test_set_calls_returns_copy(self) -> None:
        cache = SpyCache()
        cache.set("k", "v")
        calls = cache.set_calls
        calls.append(("x", "y", None))
        assert cache.set_calls == [("k", "v", None)]

    def test_delete_calls_returns_copy(self) -> None:
        cache = SpyCache()
        cache.delete("k")
        calls = cache.delete_calls
        calls.append("x")
        assert cache.delete_calls == ["k"]

    def test_flush_calls_returns_copy(self) -> None:
        cache = SpyCache()
        cache.flush()
        calls = cache.flush_calls
        calls.append(None)
        assert cache.flush_calls == [None]

    def test_delete_promise_calls_returns_copy(self) -> None:
        cache = SpyCache()
        cache.delete_promise("k")
        calls = cache.delete_promise_calls
        calls.append("x")
        assert cache.delete_promise_calls == ["k"]

    def test_set_promise_calls_returns_copy(self) -> None:
        cache = SpyCache()
        cache.set_promise("k", "v")
        calls = cache.set_promise_calls
        calls.append(("x", "y", None))
        assert cache.set_promise_calls == [("k", "v", None)]


class TestAsyncSpyCache:
    async def test_get_returns_none_for_missing_key(self) -> None:
        cache = AsyncSpyCache()
        result = await cache.get("missing")
        assert result is None

    async def test_get_returns_set_value(self) -> None:
        cache = AsyncSpyCache()
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    async def test_get_tracks_calls(self) -> None:
        cache = AsyncSpyCache()
        await cache.get("a")
        await cache.get("b")
        assert cache.get_calls == ["a", "b"]

    async def test_set_stores_value(self) -> None:
        cache = AsyncSpyCache()
        await cache.set("k", "v", ttl=60.0)
        result = await cache.get("k")
        assert result == "v"

    async def test_set_tracks_calls(self) -> None:
        cache = AsyncSpyCache()
        await cache.set("k", "v", ttl=60.0)
        assert cache.set_calls == [("k", "v", 60.0)]

    async def test_set_without_ttl(self) -> None:
        cache = AsyncSpyCache()
        await cache.set("k", "v")
        assert cache.set_calls == [("k", "v", None)]

    async def test_delete_removes_value(self) -> None:
        cache = AsyncSpyCache()
        await cache.set("k", "v")
        await cache.delete("k")
        result = await cache.get("k")
        assert result is None

    async def test_delete_tracks_calls(self) -> None:
        cache = AsyncSpyCache()
        await cache.delete("k")
        assert cache.delete_calls == ["k"]

    async def test_flush_tracks_calls(self) -> None:
        cache = AsyncSpyCache()
        await cache.flush()
        assert cache.flush_calls == [None]

    def test_set_promise_tracks_calls(self) -> None:
        cache = AsyncSpyCache()
        cache.set_promise("k", "v", ttl=30.0)
        assert cache.set_promise_calls == [("k", "v", 30.0)]

    def test_set_promise_without_ttl(self) -> None:
        cache = AsyncSpyCache()
        cache.set_promise("k", "v")
        assert cache.set_promise_calls == [("k", "v", None)]

    def test_delete_promise_tracks_calls(self) -> None:
        cache = AsyncSpyCache()
        cache.delete_promise("k")
        assert cache.delete_promise_calls == ["k"]

    def test_get_calls_returns_copy(self) -> None:
        cache = AsyncSpyCache()
        cache.get_calls.append("x")
        assert cache.get_calls == []

    def test_set_calls_returns_copy(self) -> None:
        cache = AsyncSpyCache()
        cache.set_calls.append(("x", "y", None))
        assert cache.set_calls == []

    def test_delete_calls_returns_copy(self) -> None:
        cache = AsyncSpyCache()
        cache.delete_calls.append("x")
        assert cache.delete_calls == []

    def test_flush_calls_returns_copy(self) -> None:
        cache = AsyncSpyCache()
        cache.flush_calls.append(None)
        assert cache.flush_calls == []

    def test_set_promise_calls_returns_copy(self) -> None:
        cache = AsyncSpyCache()
        cache.set_promise_calls.append(("x", "y", None))
        assert cache.set_promise_calls == []

    def test_delete_promise_calls_returns_copy(self) -> None:
        cache = AsyncSpyCache()
        cache.delete_promise_calls.append("x")
        assert cache.delete_promise_calls == []
