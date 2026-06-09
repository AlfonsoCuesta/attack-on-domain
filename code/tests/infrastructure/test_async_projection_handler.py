from __future__ import annotations

from typing import Any, cast

import pytest
from aod._internal.core.domain_exception import DomainException
from aod._internal.infrastructure.projection.projection_handler import (
    ProjectionCommandHandler as SyncProjectionCommandHandler,
    ProjectionQueryHandler as SyncProjectionQueryHandler,
)
from aod.application import ProjectionCommand, ProjectionQuery, ReadModel
from aod.infrastructure.async_ import (
    ProjectionCommandHandler,
    ProjectionQueryHandler,
)


class OrdersResponse(ReadModel):
    data: list


class GetOrders(ProjectionQuery[OrdersResponse]):
    user_id: int
    status: str | None = None


class GetOrdersHandler(ProjectionQueryHandler[GetOrders]):
    async def handle(self, query: GetOrders) -> OrdersResponse:
        return OrdersResponse(data=[
            {"id": 1, "total": 99.99, "status": query.status or "pending"},
        ])


class UpdateOrder(ProjectionCommand[None]):
    order_id: int
    status: str


class UpdateOrderHandler(ProjectionCommandHandler[UpdateOrder]):
    async def handle(self, command: UpdateOrder) -> None:
        return None


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
        assert isinstance(result, OrdersResponse)
        assert result.data[0]["id"] == 1
        assert result.data[0]["status"] == "active"

    async def test_query_handler_with_default_value(self) -> None:
        h = GetOrdersHandler()
        result = await h.handle(GetOrders(user_id=1))
        assert result.data[0]["status"] == "pending"

    async def test_query_handler_with_custom_return(self) -> None:
        class CountResponse(ReadModel):
            value: int

        class CountOrders(ProjectionQuery[CountResponse]):
            user_id: int

        class CountOrdersHandler(ProjectionQueryHandler[CountOrders]):
            async def handle(self, query: CountOrders) -> CountResponse:
                return CountResponse(value=42)

        h = CountOrdersHandler()
        result = await h.handle(CountOrders(user_id=1))
        assert result.value == 42

    async def test_handler_is_immutable(self) -> None:
        h = GetOrdersHandler()
        with pytest.raises(DomainException):
            h.handle = cast(Any, lambda p: OrdersResponse(data=[]))

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