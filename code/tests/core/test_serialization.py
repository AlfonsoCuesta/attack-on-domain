"""Tests for get_base_model."""

from __future__ import annotations

from typing import cast

from aod._internal.core.serialization import get_base_model
from aod._internal.domain.entity import RootEntity
from aod._internal.domain.value_object import ValueObject
from aod.domain import Field
from pydantic import BaseModel


class Address(ValueObject):
    street: str
    city: str


class User(RootEntity):
    id: int = Field(id=True)
    name: str
    address: Address


class TestGetBaseModel:
    def test_returns_base_model_subclass(self) -> None:
        model = get_base_model(User)
        assert issubclass(model, BaseModel)

    def test_fields_match_source(self) -> None:
        model = cast(BaseModel, get_base_model(User))
        field_names = set(model.model_fields.keys())
        assert field_names >= {"id", "name", "address"}

    def test_field_types_preserved(self) -> None:
        model = cast(BaseModel, get_base_model(User))
        assert model.model_fields["id"].annotation is int
        assert model.model_fields["name"].annotation is str
        assert model.model_fields["address"].annotation is Address

    def test_instantiation(self) -> None:
        Model = get_base_model(User)
        instance = Model(id=1, name="Alf", address=Address(street="Main", city="SF"))
        assert instance.id == 1
        assert instance.name == "Alf"
        assert instance.address.street == "Main"

    def test_root_entity(self) -> None:
        class Order(RootEntity):
            id: str = Field(id=True)
            total: float = 0.0

        model = get_base_model(Order)
        instance = model(id="abc", total=99.99)
        assert instance.id == "abc"
        assert instance.total == 99.99

    def test_value_object(self) -> None:
        class Money(ValueObject):
            amount: float
            currency: str = "USD"

        model = get_base_model(Money)
        instance = model(amount=10.0, currency="EUR")
        assert instance.amount == 10.0
        assert instance.currency == "EUR"
