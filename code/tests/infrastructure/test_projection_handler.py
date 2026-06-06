from __future__ import annotations

from typing import Any, cast

import pytest
from aod._internal.core.domain_exception import DomainException
from aod._internal.infrastructure.projection.projection_handler import (
    ProjectionQueryHandler as PH,
)
from aod._internal.infrastructure.projection.projection_store import (
    ProjectionStore as PS,
)
from aod.application import ProjectionCommand, ProjectionQuery, ReadModel
from aod.infrastructure import ProjectionCommandHandler, ProjectionQueryHandler, ProjectionStore


class OrdersResponse(ReadModel):
    data: list


class GetOrders(ProjectionQuery[OrdersResponse]):
    user_id: int
    status: str | None = None


class GetOrdersHandler(ProjectionQueryHandler[GetOrders]):
    def handle(self, query: GetOrders) -> OrdersResponse:
        return OrdersResponse(data=[
            {"id": 1, "total": 99.99, "status": query.status or "pending"},
        ])


class UpdateOrder(ProjectionCommand[None]):
    order_id: int
    status: str


class UpdateOrderHandler(ProjectionCommandHandler[UpdateOrder]):
    def handle(self, command: UpdateOrder) -> None:
        return None


class TestProjectionHandler:
    def test_query_handler_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ProjectionQueryHandler[GetOrders]()

    def test_query_handler_without_handle_is_abstract(self) -> None:
        class Incomplete(ProjectionQueryHandler[GetOrders]):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_query_handler_works(self) -> None:
        h = GetOrdersHandler()
        result = h.handle(GetOrders(user_id=1, status="active"))
        assert isinstance(result, OrdersResponse)
        assert result.data[0]["id"] == 1
        assert result.data[0]["status"] == "active"

    def test_query_handler_with_default_value(self) -> None:
        h = GetOrdersHandler()
        result = h.handle(GetOrders(user_id=1))
        assert result.data[0]["status"] == "pending"

    def test_query_handler_with_custom_return(self) -> None:
        class CountResponse(ReadModel):
            value: int

        class CountOrders(ProjectionQuery[CountResponse]):
            user_id: int

        class CountOrdersHandler(ProjectionQueryHandler[CountOrders]):
            def handle(self, query: CountOrders) -> CountResponse:
                return CountResponse(value=42)

        h = CountOrdersHandler()
        result = h.handle(CountOrders(user_id=1))
        assert result.value == 42

    def test_handler_is_immutable(self) -> None:
        h = GetOrdersHandler()
        with pytest.raises(DomainException):
            h.handle = cast(Any, lambda p: OrdersResponse(data=[]))

    def test_command_handler_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ProjectionCommandHandler[UpdateOrder]()

    def test_command_handler_without_handle_is_abstract(self) -> None:
        class Incomplete(ProjectionCommandHandler[UpdateOrder]):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_command_handler_works(self) -> None:
        h = UpdateOrderHandler()
        h.handle(UpdateOrder(order_id=1, status="shipped"))


def test_store_with_valid_query_handler() -> None:
    store = ProjectionStore(handlers=[GetOrdersHandler()])
    result = store.query(GetOrders(user_id=1, status="active"))
    assert isinstance(result, OrdersResponse)
    assert result.data[0]["status"] == "active"


def test_store_no_query_handler_registered() -> None:
    store = ProjectionStore()
    with pytest.raises(DomainException, match="No handler registered for"):
        store.query(GetOrders(user_id=1))


def test_store_with_valid_command_handler() -> None:
    store = ProjectionStore(handlers=[UpdateOrderHandler()])
    store.command(UpdateOrder(order_id=1, status="shipped"))


def test_store_no_command_handler_registered() -> None:
    store = ProjectionStore()
    with pytest.raises(DomainException, match="No handler registered for"):
        store.command(UpdateOrder(order_id=1, status="shipped"))


def test_store_with_both_handler_types() -> None:
    store = ProjectionStore(handlers=[GetOrdersHandler(), UpdateOrderHandler()])
    result = store.query(GetOrders(user_id=1))
    assert isinstance(result, OrdersResponse)
    store.command(UpdateOrder(order_id=1, status="active"))


def test_store_duplicate_handler_raises() -> None:
    with pytest.raises(DomainException, match="Duplicate handler for"):
        ProjectionStore(handlers=[GetOrdersHandler(), GetOrdersHandler()])


def test_store_duplicate_command_handler_raises() -> None:
    class AnotherHandler(ProjectionCommandHandler[UpdateOrder]):
        def handle(self, command: UpdateOrder) -> None:
            return None

    with pytest.raises(DomainException, match="Duplicate handler for"):
        ProjectionStore(handlers=[UpdateOrderHandler(), AnotherHandler()])


def test_store_invalid_handler_type_raises() -> None:
    class NoType(PH):
        def handle(self, query: object) -> object:
            return None

    with pytest.raises(DomainException, match="Cannot determine projection type for"):
        PS(handlers=[NoType()])
