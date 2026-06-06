from __future__ import annotations

from typing import Any, cast

import pytest
from aod._internal.core.domain_exception import DomainException
from aod.application import Projection
from aod.application.projection.async_ import ProjectionStore as AsyncProjectionStore
from aod.infrastructure.projection.async_ import ProjectionHandler


class GetOrders(Projection[list[dict]]):
    user_id: int
    status: str | None = None


class GetOrdersHandler(ProjectionHandler[GetOrders]):
    async def handle(self, projection: GetOrders) -> list[dict]:
        return [
            {"id": 1, "total": 99.99, "status": projection.status or "pending"},
        ]


class TestProjectionHandler:
    async def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ProjectionHandler[GetOrders]()

    async def test_without_handle_is_abstract(self) -> None:
        class Incomplete(ProjectionHandler[GetOrders]):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    async def test_concrete_handler_works(self) -> None:
        h = GetOrdersHandler()
        result = await h.handle(GetOrders(user_id=1, status="active"))
        assert isinstance(result, list)
        assert result[0]["id"] == 1
        assert result[0]["status"] == "active"

    async def test_handler_with_default_value(self) -> None:
        h = GetOrdersHandler()
        result = await h.handle(GetOrders(user_id=1))
        assert result[0]["status"] == "pending"

    async def test_invalid_generic_raises(self) -> None:
        with pytest.raises(DomainException, match="Generic parameter for"):

            class _(ProjectionHandler[str]):  # type: ignore
                async def handle(self, projection: str) -> str:
                    return projection

    async def test_handler_with_custom_return(self) -> None:
        class CountOrders(Projection[int]):
            user_id: int

        class CountOrdersHandler(ProjectionHandler[CountOrders]):
            async def handle(self, projection: CountOrders) -> int:
                return 42

        h = CountOrdersHandler()
        result = await h.handle(CountOrders(user_id=1))
        assert result == 42

    async def test_handler_is_immutable(self) -> None:
        h = GetOrdersHandler()
        with pytest.raises(DomainException):
            h.handle = cast(Any, lambda p: [])


async def test_async_store_with_valid_handler() -> None:
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore

    store = AsyncProjectionStore(handlers=[GetOrdersHandler()])
    result = await store.projection(GetOrders(user_id=1, status="active"))
    assert isinstance(result, list)
    assert result[0]["status"] == "active"


async def test_async_store_no_handler_registered() -> None:
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore

    store = AsyncProjectionStore()
    with pytest.raises(DomainException, match="No handler registered for"):
        await store.projection(GetOrders(user_id=1))


async def test_async_store_with_sync_handler() -> None:
    from aod._internal.infrastructure.projection.projection_handler import ProjectionHandler as SyncPH
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore

    class SyncHandler(SyncPH[GetOrders]):
        def handle(self, projection: GetOrders) -> list[dict]:
            return [{"id": 1, "total": 1.0}]

    store = AsyncProjectionStore(handlers=[SyncHandler()])
    result = await store.projection(GetOrders(user_id=1))
    assert isinstance(result, list)
    assert result[0]["total"] == 1.0


async def test_async_store_duplicate_handler_raises() -> None:
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore

    with pytest.raises(DomainException, match="Duplicate handler for"):
        AsyncProjectionStore(handlers=[GetOrdersHandler(), GetOrdersHandler()])


async def test_async_store_invalid_handler_type_raises() -> None:
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore
    from aod.infrastructure.projection.async_ import ProjectionHandler as AsyncPH

    class NoType(AsyncPH):
        async def handle(self, projection: object) -> object:
            return None

    with pytest.raises(DomainException, match="Cannot determine projection type for"):
        AsyncProjectionStore(handlers=[NoType()])
