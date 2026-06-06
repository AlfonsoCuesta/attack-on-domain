from __future__ import annotations

from typing import Any, cast

import pytest
from aod._internal.core.domain_exception import DomainException
from aod.application import Projection
from aod.infrastructure import ProjectionHandler


class GetOrders(Projection[list[dict]]):
    user_id: int
    status: str | None = None


class GetOrdersHandler(ProjectionHandler[GetOrders]):
    def handle(self, projection: GetOrders) -> list[dict]:
        return [
            {"id": 1, "total": 99.99, "status": projection.status or "pending"},
        ]


class TestProjectionHandler:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ProjectionHandler[GetOrders]()

    def test_without_handle_is_abstract(self) -> None:
        class Incomplete(ProjectionHandler[GetOrders]):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_handler_works(self) -> None:
        h = GetOrdersHandler()
        result = h.handle(GetOrders(user_id=1, status="active"))
        assert isinstance(result, list)
        assert result[0]["id"] == 1
        assert result[0]["status"] == "active"

    def test_handler_with_default_value(self) -> None:
        h = GetOrdersHandler()
        result = h.handle(GetOrders(user_id=1))
        assert result[0]["status"] == "pending"

    def test_invalid_generic_raises(self) -> None:
        with pytest.raises(DomainException, match="Generic parameter for"):

            class _(ProjectionHandler[str]):  # type: ignore
                def handle(self, projection: str) -> str:
                    return projection

    def test_handler_with_custom_return(self) -> None:
        class CountOrders(Projection[int]):
            user_id: int

        class CountOrdersHandler(ProjectionHandler[CountOrders]):
            def handle(self, projection: CountOrders) -> int:
                return 42

        h = CountOrdersHandler()
        result = h.handle(CountOrders(user_id=1))
        assert result == 42

    def test_handler_is_immutable(self) -> None:
        h = GetOrdersHandler()
        with pytest.raises(DomainException):
            h.handle = cast(Any, lambda p: [])


def test_store_with_valid_handler() -> None:
    from aod.infrastructure import ProjectionStore

    store = ProjectionStore(handlers=[GetOrdersHandler()])
    result = store.projection(GetOrders(user_id=1, status="active"))
    assert isinstance(result, list)
    assert result[0]["status"] == "active"


def test_store_no_handler_registered() -> None:
    from aod.infrastructure import ProjectionStore

    store = ProjectionStore()
    with pytest.raises(DomainException, match="No handler registered for"):
        store.projection(GetOrders(user_id=1))


def test_store_duplicate_handler_raises() -> None:
    from aod.infrastructure import ProjectionStore

    with pytest.raises(DomainException, match="Duplicate handler for"):
        ProjectionStore(handlers=[GetOrdersHandler(), GetOrdersHandler()])


def test_store_invalid_handler_type_raises() -> None:
    from aod._internal.infrastructure.projection.projection_store import ProjectionStore as PS
    from aod._internal.infrastructure.projection.projection_handler import ProjectionHandler as PH

    class NoType(PH):
        def handle(self, projection: object) -> object:
            return None

    with pytest.raises(DomainException, match="Cannot determine projection type for"):
        PS(handlers=[NoType()])
