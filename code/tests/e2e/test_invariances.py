from __future__ import annotations

import pytest
from aod._internal.core.domain_exception import InvarianceException
from aod._internal.core.invariances import field_invariance, invariance
from aod._internal.domain.entity import RootEntity
from aod._internal.domain.value_object import ValueObject
from aod._internal.testing.helpers import build, check_invariant


# ---------------------------------------------------------------------------
# Domain objects with invariances
# ---------------------------------------------------------------------------


class Age(ValueObject):
    value: int

    @field_invariance("value")
    def must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Age must be positive")
        if v > 150:
            raise ValueError("Age must be <= 150")
        return v


class Email(ValueObject):
    address: str

    @field_invariance("address")
    def must_be_valid_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Email must contain @")
        return v


class OrderLine(ValueObject):
    product: str
    quantity: int
    unit_price: int

    @field_invariance("quantity")
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_invariance("unit_price")
    def price_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v


class Order(RootEntity):
    id: str
    lines: list[OrderLine]
    total: int = 0

    @invariance
    def total_must_match_lines(self) -> None:
        expected = sum(line.quantity * line.unit_price for line in self.lines)
        if self.total != expected:
            raise ValueError(f"Total {self.total} does not match lines total {expected}")


class User(RootEntity):
    id: str
    name: str
    email: Email
    age: Age

    @invariance(name="adult_check")
    def must_be_adult(self) -> None:
        if self.age.value < 18:
            raise ValueError("User must be at least 18 years old")


# ===========================================================================
# TESTS
# ===========================================================================


class TestFieldInvariance:
    def test_valid_value_passes(self) -> None:
        a = Age(value=25)
        assert a.value == 25

    def test_negative_value_raises(self) -> None:
        with pytest.raises(InvarianceException, match="Age must be positive"):
            Age(value=-1)

    def test_too_large_value_raises(self) -> None:
        with pytest.raises(InvarianceException, match="Age must be <= 150"):
            Age(value=200)

    def test_valid_email_passes(self) -> None:
        e = Email(address="user@example.com")
        assert e.address == "user@example.com"

    def test_invalid_email_raises(self) -> None:
        with pytest.raises(InvarianceException, match="Email must contain @"):
            Email(address="not-an-email")

    def test_zero_quantity_raises(self) -> None:
        with pytest.raises(InvarianceException, match="Quantity must be positive"):
            OrderLine(product="A", quantity=0, unit_price=100)

    def test_negative_quantity_raises(self) -> None:
        with pytest.raises(InvarianceException, match="Quantity must be positive"):
            OrderLine(product="A", quantity=-1, unit_price=100)

    def test_negative_price_raises(self) -> None:
        with pytest.raises(InvarianceException, match="Price cannot be negative"):
            OrderLine(product="A", quantity=1, unit_price=-10)

    def test_build_skips_field_invariances(self) -> None:
        a = build(Age, value=-5)
        assert a.value == -5

    def test_build_skips_invalid_email(self) -> None:
        e = build(Email, address="bad")
        assert e.address == "bad"


class TestModelInvariance:
    def test_valid_order_passes(self) -> None:
        order = Order(
            id="ORD-001",
            lines=[
                OrderLine(product="A", quantity=2, unit_price=100),
                OrderLine(product="B", quantity=1, unit_price=50),
            ],
            total=250,
        )
        assert order.total == 250

    def test_invalid_total_raises(self) -> None:
        with pytest.raises(InvarianceException, match="Total"):
            Order(
                id="ORD-001",
                lines=[
                    OrderLine(product="A", quantity=2, unit_price=100),
                ],
                total=999,
            )

    def test_valid_user_passes(self) -> None:
        user = User(
            id="U-001",
            name="Alice",
            email=Email(address="alice@example.com"),
            age=Age(value=30),
        )
        assert user.name == "Alice"

    def test_underage_user_raises(self) -> None:
        with pytest.raises(InvarianceException, match="adult_check|at least 18"):
            User(
                id="U-002",
                name="Bob",
                email=Email(address="bob@example.com"),
                age=Age(value=15),
            )

    def test_build_skips_model_invariances(self) -> None:
        order = build(
            Order,
            id="ORD-001",
            lines=[
                OrderLine(product="A", quantity=2, unit_price=100),
            ],
            total=999,
        )
        assert order.total == 999


class TestCheckInvariantHelper:
    def test_check_field_invariant(self) -> None:
        check_invariant(Age, "must_be_positive", value=25)

    def test_check_field_invariant_fails(self) -> None:
        with pytest.raises(InvarianceException, match="Age must be positive"):
            check_invariant(Age, "must_be_positive", value=-1)

    def test_check_model_invariant(self) -> None:
        check_invariant(
            Order,
            "total_must_match_lines",
            id="ORD-001",
            lines=[OrderLine(product="A", quantity=2, unit_price=100)],
            total=200,
        )

    def test_check_model_invariant_fails(self) -> None:
        with pytest.raises(InvarianceException, match="Total"):
            check_invariant(
                Order,
                "total_must_match_lines",
                id="ORD-001",
                lines=[OrderLine(product="A", quantity=2, unit_price=100)],
                total=999,
            )

    def test_check_invariant_by_name(self) -> None:
        check_invariant(
            User,
            "adult_check",
            id="U-001",
            name="Alice",
            email=build(Email, address="a@b.com"),
            age=Age(value=20),
        )

    def test_check_invariant_unknown_name_raises(self) -> None:
        with pytest.raises(ValueError, match="No invariant named"):
            check_invariant(Age, "nonexistent", value=1)
