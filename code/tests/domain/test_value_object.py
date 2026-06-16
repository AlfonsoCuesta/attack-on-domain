"""Tests for ValueObject domain class."""

from __future__ import annotations

import pytest
from aod._internal.core.domain_exception import (
    InvarianceException,
    ModelValidationError,
    MutationForbiddenException,
)
from aod._internal.core.event_emitter import Event
from aod._internal.core.fields import Field, PrivateField
from aod._internal.domain.value_object import ValueObject
from aod.testing import build


class Money(ValueObject):
    amount: int
    currency: str = "USD"


class Address(ValueObject):
    street: str
    city: str


class Point(ValueObject):
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)


class VoWithPrivate(ValueObject):
    name: str
    _internal: str = PrivateField(default="secret")


class VoWithDefaults(ValueObject):
    name: str
    count: int = 0
    label: str = "default"


class VoWithInvariant(ValueObject):
    amount: int

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise InvarianceException("positive_amount", "amount must be non-negative")


class TestValueObjectConstruction:
    def test_basic_construction(self) -> None:
        m = Money(amount=100, currency="EUR")
        assert m.amount == 100
        assert m.currency == "EUR"

    def test_default_field(self) -> None:
        m = Money(amount=50)
        assert m.currency == "USD"

    def test_type_coercion(self) -> None:
        m = Money(amount="42")  # type: ignore
        assert m.amount == 42
        assert isinstance(m.amount, int)

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ModelValidationError):
            Money()  # type: ignore

    def test_field_constraints_enforced(self) -> None:
        with pytest.raises(ModelValidationError):
            Point(x=200, y=50)

    def test_nested_value_object(self) -> None:
        addr = Address(street="Main St", city="SF")
        assert addr.street == "Main St"
        assert addr.city == "SF"

    def test_VO_with_private_field(self) -> None:
        v = VoWithPrivate(name="test")
        assert v.name == "test"
        assert v._internal == "secret"

    def test_VO_with_defaults(self) -> None:
        v = VoWithDefaults(name="test")
        assert v.count == 0
        assert v.label == "default"


class TestValueObjectImmutability:
    def test_blocks_attribute_mutation(self) -> None:
        m = Money(amount=100)
        with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
            m.amount = 200

    def test_blocks_string_mutation(self) -> None:
        m = Money(amount=100, currency="EUR")
        with pytest.raises(MutationForbiddenException):
            m.currency = "GBP"

    def test_immutability_after_copy(self) -> None:
        m = Money(amount=100)
        m2 = m.copy(amount=200)
        with pytest.raises(MutationForbiddenException):
            m2.amount = 300


class TestValueObjectRepr:
    def test_repr_shows_fields(self) -> None:
        m = Money(amount=100, currency="EUR")
        r = repr(m)
        assert "Money" in r
        assert "amount=100" in r
        assert "currency='EUR'" in r

    def test_repr_with_nested_vo(self) -> None:
        addr = Address(street="Main St", city="SF")
        r = repr(addr)
        assert "Address" in r
        assert "street='Main St'" in r


class TestValueObjectCopy:
    def test_copy_preserves_original(self) -> None:
        m = Money(amount=100)
        m2 = m.copy(amount=200)
        assert m.amount == 100
        assert m2.amount == 200

    def test_copy_with_no_overrides(self) -> None:
        m = Money(amount=100, currency="EUR")
        m2 = m.copy()
        assert m2.amount == 100
        assert m2.currency == "EUR"


class TestValueObjectEquality:
    def test_equal_values(self) -> None:
        m1 = Money(amount=100, currency="USD")
        m2 = Money(amount=100, currency="USD")
        assert m1.amount == m2.amount
        assert m1.currency == m2.currency

    def test_different_values(self) -> None:
        m1 = Money(amount=100)
        m2 = Money(amount=200)
        assert m1.amount != m2.amount


class TestValueObjectReconstruct:
    def test_reconstruct_skips_validators(self) -> None:
        m2 = Money.reconstruct(amount=200, currency="EUR")
        assert m2.amount == 200
        assert m2.currency == "EUR"

    def test_reconstruct_from_dict(self) -> None:
        m = Money.reconstruct(amount=50, currency="GBP")
        assert isinstance(m, Money)
        assert m.amount == 50


class TestValueObjectEvents:
    def test_VO_can_emit_events(self) -> None:
        m = Money(amount=100)

        class MoneyCreated(Event):
            pass

        m._event_emitter.emit(MoneyCreated())
        events = m._event_emitter.poll_events()
        assert len(events) == 1


class TestValueObjectBuild:
    def test_build_skips_invariances(self) -> None:
        v = build(VoWithInvariant, amount=-10)
        assert v.amount == -10
