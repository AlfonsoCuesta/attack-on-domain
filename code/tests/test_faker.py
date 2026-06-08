from __future__ import annotations

from aod._internal.domain.entity import RootEntity
from aod._internal.domain.service import Service
from aod._internal.domain.value_object import ValueObject
from aod.testing import FakeDomain
from aod._internal.testing.faker.faker import _flatten, _to_domain
from typing import get_args, get_origin


# ── domain types used across tests ──────────────────────────────────────────


class Address(ValueObject):
    street: str
    city: str


class User(RootEntity):
    id: int
    name: str
    address: Address


class Tag(ValueObject):
    name: str
    count: int


# ── _flatten ─────────────────────────────────────────────────────────────────


class TestFlatten:
    def test_base_guarded_returns_raw_model(self) -> None:
        assert _flatten(Address) is Address.__raw_model__

    def test_plain_type_returns_itself(self) -> None:
        assert _flatten(int) is int
        assert _flatten(str) is str

    def test_union_with_none_returns_single(self) -> None:
        assert _flatten(Address | None) is Address.__raw_model__

    def test_union_with_multiple_non_none_types(self) -> None:
        result = _flatten(str | int | None)
        assert result == str | int

    def test_generic_without_none(self) -> None:
        assert _flatten(list[int]) == list[int]
        result = _flatten(dict[str, Address])
        assert get_origin(result) is dict
        assert get_args(result) == (str, Address.__raw_model__)

    def test_nested_base_guarded_in_generic(self) -> None:
        result = _flatten(list[Address])
        assert get_origin(result) is list
        assert get_args(result) == (Address.__raw_model__,)


# ── _to_domain ───────────────────────────────────────────────────────────────


class TestToDomain:
    def test_none_value_returns_none(self) -> None:
        assert _to_domain(str, None) is None

    def test_raw_model_converts_to_domain(self) -> None:
        raw = Address.__raw_model__(street="S", city="C")
        result = _to_domain(Address, raw)
        assert isinstance(result, Address)
        assert result.street == "S"

    def test_non_raw_model_value_returned_as_is(self) -> None:
        assert _to_domain(Address, "not_a_model") == "not_a_model"

    def test_list_of_base_guarded(self) -> None:
        raw = Address.__raw_model__(street="S", city="C")
        result = _to_domain(list[Address], [raw])
        assert isinstance(result[0], Address)

    def test_dict_with_base_guarded_values(self) -> None:
        raw = Address.__raw_model__(street="S", city="C")
        result = _to_domain(dict[str, Address], {"home": raw})
        assert isinstance(result["home"], Address)

    def test_set_of_plain_type(self) -> None:
        result = _to_domain(set[str], {"a", "b"})
        assert result == {"a", "b"}

    def test_set_of_base_guarded(self) -> None:
        result = _to_domain(set[Address], set())
        assert result == set()

    def test_tuple_of_base_guarded(self) -> None:
        raw = Address.__raw_model__(street="S", city="C")
        result = _to_domain(tuple[Address, ...], (raw,))
        assert isinstance(result[0], Address)

    def test_plain_type_returned_as_is(self) -> None:
        assert _to_domain(str, "hello") == "hello"


# ── FakeDomain ───────────────────────────────────────────────────────────────


class TestFakeDomainConstructor:
    def test_non_domain_raises(self) -> None:
        class NotDomain:
            pass

        try:
            FakeDomain(NotDomain)
            msg = "expected TypeError"
            raise AssertionError(msg)
        except TypeError as e:
            assert "Entity" in str(e) or "ValueObject" in str(e)

    def test_service_raises(self) -> None:
        class MyService(Service):
            pass

        try:
            FakeDomain(MyService)
            msg = "expected TypeError"
            raise AssertionError(msg)
        except TypeError as e:
            assert "Entity" in str(e) or "ValueObject" in str(e)


class TestFakeDomainBuild:
    def test_entity_with_nested_value_object(self) -> None:
        JessicaUser = FakeDomain(User)
        u = JessicaUser(id=1, name="Alf", address=Address(street="S", city="C"))
        assert isinstance(u, User)
        assert u.id == 1
        assert u.name == "Alf"
        assert u.address.street == "S"

    def test_defaults_are_applied(self) -> None:
        JessicaUser = FakeDomain(User, name="Jessica")
        u = JessicaUser(id=1, address=Address(street="S", city="C"))
        assert u.name == "Jessica"
        assert u.id == 1

    def test_call_overrides_defaults(self) -> None:
        JessicaUser = FakeDomain(User, name="Jessica")
        u = JessicaUser(id=1, name="Pablo", address=Address(street="S", city="C"))
        assert u.name == "Pablo"

    def test_call_overrides_partial(self) -> None:
        JessicaUser = FakeDomain(User, name="Jessica")
        u = JessicaUser(id=1, address=Address(street="S", city="C"))
        assert u.name == "Jessica"

    def test_value_object(self) -> None:
        class Coord(ValueObject):
            x: float
            y: float

        CoordFactory = FakeDomain(Coord)
        c = CoordFactory(x=1.0, y=2.0)
        assert isinstance(c, Coord)
        assert c.x == 1.0

    def test_fills_missing_fields_with_fake_data(self) -> None:
        JessicaUser = FakeDomain(User, name="Jessica")
        u = JessicaUser(id=1, address=Address(street="S", city="C"))
        assert u.name == "Jessica"
        assert u.id == 1
        assert isinstance(u.address, Address)
        assert u.address.street == "S"


class TestFakeDomainBatch:
    def test_batch_with_count(self) -> None:
        JessicaUser = FakeDomain(User)
        users = JessicaUser.batch(3, [{"id": 1}, {"id": 2}, {"id": 3}])
        assert len(users) == 3
        assert [u.id for u in users] == [1, 2, 3]

    def test_batch_without_overrides(self) -> None:
        JessicaUser = FakeDomain(User, name="Jessica")
        users = JessicaUser.batch(3, [{"id": 1}, {"id": 2}, {"id": 3}])
        assert len(users) == 3
        for u in users:
            assert u.name == "Jessica"

    def test_batch_no_list(self) -> None:
        JessicaUser = FakeDomain(User, name="Jessica")
        users = JessicaUser.batch(2)
        assert len(users) == 2
        for u in users:
            assert u.name == "Jessica"
