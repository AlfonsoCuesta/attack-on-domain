"""Tests for Infrastructure schema class."""

from __future__ import annotations

from aod._internal.application.cache.cache_key import CacheInvalidation, CacheKey
from aod._internal.application.cache.null_cache import NullCache
from aod._internal.application.contracts import Query
from aod._internal.domain.entity import RootEntity
from aod._internal.infrastructure.container import AdapterContainer
from aod._internal.schema import Infrastructure
from aod.domain import Field


class Order(RootEntity):
    id: str = Field(id=True)
    total: float = 0.0


class GetOrder(Query[Order, Order | None]):
    order_id: str


class TestInfrastructureCaches:
    def test_caches_field(self) -> None:
        infra = Infrastructure(caches=[NullCache()])

        assert infra.caches == (NullCache,)
        assert infra.cache_keys == ()

    def test_cache_key_extraction(self) -> None:
        class GetOrderKey(CacheKey[GetOrder]):
            ttl = 60.0

            def key(self, query: GetOrder) -> str:
                return f"order:{query.order_id}"

            def invalidate(self) -> list[CacheInvalidation]:
                return []

        cache = NullCache(keys=[GetOrderKey()])
        infra = Infrastructure(caches=[cache])

        assert NullCache in infra.caches
        assert GetOrderKey in infra.cache_keys

    def test_adapter_caches_merged_with_explicit(self) -> None:
        adapter = AdapterContainer(caches=[NullCache()])
        explicit = NullCache()
        infra = Infrastructure(caches=[explicit], adapters=[adapter])

        assert NullCache in infra.caches
        assert adapter in infra.adapters
