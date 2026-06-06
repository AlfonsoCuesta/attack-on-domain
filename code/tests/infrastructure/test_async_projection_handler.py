from __future__ import annotations

from typing import Any, cast

import pytest
from aod._internal.core.domain_exception import DomainException
from aod.application import ProjectionCommand, ProjectionQuery
from aod.application.projection.async_ import ProjectionStore as AsyncProjectionStore
from aod.infrastructure.projection.async_ import ProjectionCommandHandler, ProjectionQueryHandler


class GetOrders(ProjectionQuery[list[dict]]):
    user_id: int
    status: str | None = None


class GetOrdersHandler(ProjectionQueryHandler[GetOrders]):
    async def handle(self, query: GetOrders) -> list[dict]:
        return [
            {"id": 1, "total": 99.99, "status": query.status or "pending"},
        ]


class UpdateOrder(ProjectionCommand[None]):
    order_id: int
    status: str


class UpdateOrderHandler(ProjectionCommandHandler[UpdateOrder]):
    async def handle(self, command: UpdateOrder) -> None:
        pass


class TestProjectionHandler:
    async def test_query_handler_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ProjectionQueryHandler[GetOrders]()

    async def test_query_handler_without_handle_is_abstract(self) -> None:
        class Incomplete(ProjectionQueryHandler[GetOrders]):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    async def test_concrete_query_handler_works(self) -> None:
        h = GetOrdersHandler()
        result = await h.handle(GetOrders(user_id=1, status="active"))
        assert isinstance(result, list)
        assert result[0]["id"] == 1
        assert result[0]["status"] == "active"

    async def test_query_handler_with_default_value(self) -> None:
        h = GetOrdersHandler()
        result = await h.handle(GetOrders(user_id=1))
        assert result[0]["status"] == "pending"

    async def test_invalid_query_handler_generic_raises(self) -> None:
        with pytest.raises(DomainException, match="Generic parameter for"):

            class _(ProjectionQueryHandler[str]):  # type: ignore
                async def handle(self, query: str) -> str:
                    return query

    async def test_query_handler_with_custom_return(self) -> None:
        class CountOrders(ProjectionQuery[int]):
            user_id: int

        class CountOrdersHandler(ProjectionQueryHandler[CountOrders]):
            async def handle(self, query: CountOrders) -> int:
                return 42

        h = CountOrdersHandler()
        result = await h.handle(CountOrders(user_id=1))
        assert result == 42

    async def test_handler_is_immutable(self) -> None:
        h = GetOrdersHandler()
        with pytest.raises(DomainException):
            h.handle = cast(Any, lambda p: [])

    async def test_command_handler_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ProjectionCommandHandler[UpdateOrder]()

    async def test_command_handler_without_handle_is_abstract(self) -> None:
        class Incomplete(ProjectionCommandHandler[UpdateOrder]):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    async def test_command_handler_works(self) -> None:
        h = UpdateOrderHandler()
        await h.handle(UpdateOrder(order_id=1, status="shipped"))

    async def test_invalid_command_handler_generic_raises(self) -> None:
        with pytest.raises(DomainException, match="Generic parameter for"):

            class _(ProjectionCommandHandler[str]):  # type: ignore
                async def handle(self, command: str) -> None:
                    pass


async def test_async_store_with_valid_query_handler() -> None:
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore

    store = AsyncProjectionStore(handlers=[GetOrdersHandler()])
    result = await store.query(GetOrders(user_id=1, status="active"))
    assert isinstance(result, list)
    assert result[0]["status"] == "active"


async def test_async_store_no_query_handler_registered() -> None:
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore

    store = AsyncProjectionStore()
    with pytest.raises(DomainException, match="No handler registered for"):
        await store.query(GetOrders(user_id=1))


async def test_async_store_with_sync_query_handler() -> None:
    from aod._internal.infrastructure.projection.projection_handler import ProjectionQueryHandler as SyncPQH
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore

    class SyncHandler(SyncPQH[GetOrders]):
        def handle(self, query: GetOrders) -> list[dict]:
            return [{"id": 1, "total": 1.0}]

    store = AsyncProjectionStore(handlers=[SyncHandler()])
    result = await store.query(GetOrders(user_id=1))
    assert isinstance(result, list)
    assert result[0]["total"] == 1.0


async def test_async_store_with_valid_command_handler() -> None:
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore

    store = AsyncProjectionStore(handlers=[UpdateOrderHandler()])
    await store.command(UpdateOrder(order_id=1, status="shipped"))


async def test_async_store_no_command_handler_registered() -> None:
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore

    store = AsyncProjectionStore()
    with pytest.raises(DomainException, match="No handler registered for"):
        await store.command(UpdateOrder(order_id=1, status="shipped"))


async def test_async_store_with_sync_command_handler() -> None:
    from aod._internal.infrastructure.projection.projection_handler import ProjectionCommandHandler as SyncPCH
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore

    class SyncHandler(SyncPCH[UpdateOrder]):
        def handle(self, command: UpdateOrder) -> None:
            pass

    store = AsyncProjectionStore(handlers=[SyncHandler()])
    await store.command(UpdateOrder(order_id=1, status="shipped"))


async def test_async_store_with_both_handler_types() -> None:
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore

    store = AsyncProjectionStore(handlers=[GetOrdersHandler(), UpdateOrderHandler()])
    result = await store.query(GetOrders(user_id=1))
    assert isinstance(result, list)
    await store.command(UpdateOrder(order_id=1, status="active"))


async def test_async_store_duplicate_handler_raises() -> None:
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore

    with pytest.raises(DomainException, match="Duplicate handler for"):
        AsyncProjectionStore(handlers=[GetOrdersHandler(), GetOrdersHandler()])


async def test_async_store_duplicate_command_handler_raises() -> None:
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore

    class AnotherHandler(ProjectionCommandHandler[UpdateOrder]):
        async def handle(self, command: UpdateOrder) -> None:
            pass

    with pytest.raises(DomainException, match="Duplicate handler for"):
        AsyncProjectionStore(handlers=[UpdateOrderHandler(), AnotherHandler()])


async def test_async_store_invalid_handler_type_raises() -> None:
    from aod.infrastructure.projection.async_ import ProjectionStore as AsyncProjectionStore
    from aod.infrastructure.projection.async_ import ProjectionQueryHandler as AsyncPH

    class NoType(AsyncPH):
        async def handle(self, query: object) -> object:
            return None

    with pytest.raises(DomainException, match="Cannot determine projection type for"):
        AsyncProjectionStore(handlers=[NoType()])
