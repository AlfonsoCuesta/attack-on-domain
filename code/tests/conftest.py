"""Shared test fixtures for the test suite."""

from __future__ import annotations

import pytest
from aod._internal.core.event_emitter import Event
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.value_object import ValueObject
from aod.domain import Field


class UserCreated(Event):
    user_id: int


class OrderPlaced(Event):
    order_id: int


class Address(ValueObject):
    street: str
    city: str


class User(RootEntity):
    id: int = Field(id=True)
    name: str
    address: Address


class SimpleEntity(Entity):
    id: int = Field(id=True)
    value: str


class Money(ValueObject):
    amount: int
    currency: str = "USD"


@pytest.fixture
def address() -> Address:
    return Address(street="Main St", city="Springfield")


@pytest.fixture
def user(address: Address) -> User:
    return User(id=1, name="Alice", address=address)
