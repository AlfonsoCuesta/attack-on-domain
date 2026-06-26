"""Shared test fixtures for the test suite."""

from __future__ import annotations

import pytest

from aod._internal.core.event_emitter import Event
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.entity_id import EntityId
from aod._internal.domain.value_object import ValueObject


class UserCreated(Event):
    user_id: int


class OrderPlaced(Event):
    order_id: int


class Address(ValueObject):
    street: str
    city: str


class IntId(EntityId):
    value: int


class StrId(EntityId):
    value: str


class User(RootEntity):
    id: IntId
    name: str
    address: Address


class SimpleEntity(Entity):
    id: IntId
    value: str


class Money(ValueObject):
    amount: int
    currency: str = "USD"


@pytest.fixture
def address() -> Address:
    return Address(street="Main St", city="Springfield")


@pytest.fixture
def user(address: Address) -> User:
    return User(id=IntId(value=1), name="Alice", address=address)
