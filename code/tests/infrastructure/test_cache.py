from __future__ import annotations

import pytest
from aod._internal.infrastructure.cache.cache import Cache, AsyncCache, _SetItem


class ConcreteCache(Cache):
    def get(self, key: str) -> object:
        return None

    def set(self, key: str, value: object, ttl: float | None = None) -> None:
        pass

    def delete(self, key: str) -> None:
        pass


class ConcreteAsyncCache(AsyncCache):
    async def get(self, key: str) -> object:
        return None

    async def set(self, key: str, value: object, ttl: float | None = None) -> None:
        pass

    async def delete(self, key: str) -> None:
        pass


class TestSetItem:
    def test_default_ttl_is_none(self) -> None:
        item = _SetItem(key="k", value="v")
        assert item.key == "k"
        assert item.value == "v"
        assert item.ttl is None

    def test_with_ttl(self) -> None:
        item = _SetItem(key="k", value="v", ttl=60.0)
        assert item.ttl == 60.0


class TestCache:
    def test_set_promise(self) -> None:
        c = ConcreteCache()
        c.set_promise("a", 1)
        assert len(c._set_items) == 1
        assert c._set_items[0].key == "a"

    def test_delete_promise(self) -> None:
        c = ConcreteCache()
        c.delete_promise("x")
        assert len(c._delete_items) == 1
        assert c._delete_items[0] == "x"

    def test_flush_with_both(self) -> None:
        c = ConcreteCache()
        c.set_promise("a", 1)
        c.set_promise("b", 2, ttl=30.0)
        c.delete_promise("x")
        c.flush()
        assert len(c._set_items) == 0
        assert len(c._delete_items) == 0

    def test_flush_empty(self) -> None:
        c = ConcreteCache()
        c.flush()
        assert len(c._set_items) == 0
        assert len(c._delete_items) == 0

    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            Cache()


class TestAsyncCache:
    async def test_set_promise(self) -> None:
        c = ConcreteAsyncCache()
        c.set_promise("a", 1)
        assert len(c._set_items) == 1

    async def test_delete_promise(self) -> None:
        c = ConcreteAsyncCache()
        c.delete_promise("x")
        assert len(c._delete_items) == 1

    async def test_flush_with_both(self) -> None:
        c = ConcreteAsyncCache()
        c.set_promise("a", 1)
        c.set_promise("b", 2, ttl=30.0)
        c.delete_promise("x")
        await c.flush()
        assert len(c._set_items) == 0
        assert len(c._delete_items) == 0

    async def test_flush_empty(self) -> None:
        c = ConcreteAsyncCache()
        await c.flush()
        assert len(c._set_items) == 0
        assert len(c._delete_items) == 0

    async def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            AsyncCache()
