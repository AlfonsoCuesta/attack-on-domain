from __future__ import annotations

import pytest
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.value_object import ValueObject
from aod.application import Projection
from aod.application.projection import Projection as ProjectionDirect


class User(RootEntity):
    id: int
    name: str


class Address(ValueObject):
    street: str
    city: str


class LineItem(Entity):
    sku: str
    qty: int


class TestProjection:
    def test_can_be_instantiated(self) -> None:
        class GetOrders(Projection[list[dict]]):
            user_id: int

        p = GetOrders(user_id=1)
        assert p.user_id == 1

    def test_is_immutable(self) -> None:
        class GetOrders(Projection[list[dict]]):
            user_id: int

        p = GetOrders(user_id=1)
        with pytest.raises(MutationForbiddenException):
            p.user_id = 99

    def test_repr(self) -> None:
        class GetOrders(Projection[list[dict]]):
            user_id: int
            status: str | None = None

        p = GetOrders(user_id=1, status="active")
        rep = repr(p)
        assert "GetOrders" in rep
        assert "user_id=1" in rep
        assert "active" in rep

    def test_default_values(self) -> None:
        class GetOrders(Projection[list[dict]]):
            user_id: int
            status: str | None = None

        p = GetOrders(user_id=1)
        assert p.status is None

    def test_can_have_entity_field(self) -> None:
        class GetLineItems(Projection[list[dict]]):
            item: LineItem

        p = GetLineItems(item=LineItem(sku="ABC", qty=5))
        assert p.item.sku == "ABC"

    def test_can_have_root_entity_field(self) -> None:
        class GetUserInfo(Projection[dict]):
            user: User

        p = GetUserInfo(user=User(id=1, name="Alice"))
        assert p.user.name == "Alice"

    def test_can_have_value_object_field(self) -> None:
        class GetAddressInfo(Projection[dict]):
            address: Address

        p = GetAddressInfo(address=Address(street="123 Main", city="NYC"))
        assert p.address.city == "NYC"

    def test_can_have_primitive_result_type(self) -> None:
        class CountOrders(Projection[int]):
            user_id: int

        p = CountOrders(user_id=1)
        assert p.user_id == 1

    def test_can_have_any_nested_type(self) -> None:
        class ComplexProjection(Projection[tuple[int, User | None, list[LineItem]]]):
            query: str

        p = ComplexProjection(query="test")
        assert p.query == "test"

    def test_no_fields_still_works(self) -> None:
        class AllOrders(Projection[list[dict]]):
            pass

        p = AllOrders()
        assert isinstance(p, Projection)

    def test_direct_module_import_works(self) -> None:
        class DirectOrder(ProjectionDirect[list[dict]]):
            user_id: int

        p = DirectOrder(user_id=1)
        assert p.user_id == 1
