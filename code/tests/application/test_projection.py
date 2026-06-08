from __future__ import annotations

import pytest
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.value_object import ValueObject
from aod.application import ProjectionCommand, ProjectionQuery, ReadModel
from aod._internal.application.projection import ProjectionQuery as ProjectionQueryDirect


class User(RootEntity):
    id: int
    name: str


class Address(ValueObject):
    street: str
    city: str


class LineItem(Entity):
    sku: str
    qty: int


class OrdersResponse(ReadModel):
    data: list


class TestProjection:
    def test_can_be_instantiated(self) -> None:
        class GetOrders(ProjectionQuery[OrdersResponse]):
            user_id: int

        p = GetOrders(user_id=1)
        assert p.user_id == 1

    def test_is_immutable(self) -> None:
        class GetOrders(ProjectionQuery[OrdersResponse]):
            user_id: int

        p = GetOrders(user_id=1)
        with pytest.raises(MutationForbiddenException):
            p.user_id = 99

    def test_repr(self) -> None:
        class GetOrders(ProjectionQuery[OrdersResponse]):
            user_id: int
            status: str | None = None

        p = GetOrders(user_id=1, status="active")
        rep = repr(p)
        assert "GetOrders" in rep
        assert "user_id=1" in rep
        assert "active" in rep

    def test_default_values(self) -> None:
        class GetOrders(ProjectionQuery[OrdersResponse]):
            user_id: int
            status: str | None = None

        p = GetOrders(user_id=1)
        assert p.status is None

    def test_can_have_entity_field(self) -> None:
        class GetLineItems(ProjectionQuery[OrdersResponse]):
            item: LineItem

        p = GetLineItems(item=LineItem(sku="ABC", qty=5))
        assert p.item.sku == "ABC"

    def test_can_have_root_entity_field(self) -> None:
        class GetUserInfo(ProjectionQuery[OrdersResponse]):
            user: User

        p = GetUserInfo(user=User(id=1, name="Alice"))
        assert p.user.name == "Alice"

    def test_can_have_value_object_field(self) -> None:
        class GetAddressInfo(ProjectionQuery[OrdersResponse]):
            address: Address

        p = GetAddressInfo(address=Address(street="123 Main", city="NYC"))
        assert p.address.city == "NYC"

    def test_can_have_primitive_fields(self) -> None:
        class CountOrders(ProjectionQuery[OrdersResponse]):
            user_id: int

        p = CountOrders(user_id=1)
        assert p.user_id == 1

    def test_no_fields_still_works(self) -> None:
        class AllOrders(ProjectionQuery[OrdersResponse]):
            pass

        p = AllOrders()
        assert isinstance(p, ProjectionQuery)

    def test_direct_module_import_works(self) -> None:
        class DirectOrder(ProjectionQueryDirect[OrdersResponse]):
            user_id: int

        p = DirectOrder(user_id=1)
        assert p.user_id == 1

    def test_projection_command(self) -> None:
        class SaveOrder(ProjectionCommand[None]):
            order_id: int
            total: float

        cmd = SaveOrder(order_id=42, total=99.99)
        assert cmd.order_id == 42
        assert cmd.total == 99.99

    def test_projection_command_is_immutable(self) -> None:
        class SaveOrder(ProjectionCommand[None]):
            order_id: int

        cmd = SaveOrder(order_id=42)
        with pytest.raises(MutationForbiddenException):
            cmd.order_id = 99

    def test_allows_none_result(self) -> None:
        class VoidResponse(ReadModel):
            pass

        class _(ProjectionCommand[VoidResponse]):
            order_id: int

    def test_allows_union_read_model_none(self) -> None:
        class OptionalModel(ReadModel):
            value: int

        class _(ProjectionQuery[OptionalModel | None]):
            user_id: int
