"""Tests for Entity and RootEntity domain classes."""

from __future__ import annotations

import pytest
from aod._internal.core.domain_exception import (
    ModelValidationError,
    MutationForbiddenException,
    NoIdentityFieldException,
    TooManyIdentityFieldsException,
)
from aod._internal.core.event_emitter import Event, EventCollector
from aod._internal.core.fields import Field, PrivateField
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.value_object import ValueObject


class Address(ValueObject):
    street: str
    city: str


class UserCreated(Event):
    user_id: int


class User(RootEntity):
    id: int = Field(id=True)
    name: str
    address: Address


class SimpleEntity(Entity):
    id: int = Field(id=True)
    value: str


class EntityWithPrivate(RootEntity):
    id: int = Field(id=True)
    _secret: str = PrivateField(default="hidden")


class EntityWithDefaults(RootEntity):
    id: int = Field(id=True)
    name: str = "unknown"
    score: float = 0.0


class TestEntityIdentityExceptions:
    def test_entity_with_multiple_id_fields_raises(self) -> None:
        with pytest.raises(TooManyIdentityFieldsException):

            class MultiIdEntity(Entity):
                id1: int = Field(id=True)
                id2: str = Field(id=True)

    def test_entity_without_id_field_raises(self) -> None:
        with pytest.raises(NoIdentityFieldException):

            class NoIdEntity(Entity):
                name: str


class test_entity_is_not_root:
    def test_entity_with_fields(self) -> None:
        e = SimpleEntity(id=1, value="test")
        assert e.id == 1
        assert e.value == "test"

    def test_root_entity_with_nested_vo(self) -> None:
        addr = Address(street="Main St", city="Springfield")
        u = User(id=1, name="Alice", address=addr)
        assert u.address.street == "Main St"
        assert u.address.city == "Springfield"

    def test_entity_with_default_fields(self) -> None:
        e = EntityWithDefaults(id=1)
        assert e.name == "unknown"
        assert e.score == 0.0

    def test_entity_type_coercion(self) -> None:
        e = SimpleEntity(id=42, value="test")
        assert e.id == 42
        assert isinstance(e.id, int)

    def test_entity_missing_required_field_raises(self) -> None:
        with pytest.raises(ModelValidationError):
            SimpleEntity()  # type: ignore

    def test_entity_with_private_field(self) -> None:
        e = EntityWithPrivate(id=1)
        assert e._secret == "hidden"


class TestEntityImmutability:
    def test_entity_blocks_attribute_mutation(self) -> None:
        e = SimpleEntity(id=1, value="test")
        with pytest.raises(MutationForbiddenException):
            e.id = 2

    def test_entity_blocks_string_mutation(self) -> None:
        e = SimpleEntity(id=1, value="test")
        with pytest.raises(MutationForbiddenException):
            e.value = "changed"

    def test_root_entity_blocks_mutation(self) -> None:
        u = User(id=1, name="Alice", address=Address(street="Main St", city="SF"))
        with pytest.raises(MutationForbiddenException):
            u.name = "Bob"


class TestEntityRepr:
    def test_entity_repr(self) -> None:
        e = SimpleEntity(id=1, value="test")
        r = repr(e)
        assert "SimpleEntity" in r
        assert "id=1" in r
        assert "value='test'" in r

    def test_root_entity_repr(self) -> None:
        addr = Address(street="Main St", city="SF")
        u = User(id=1, name="Alice", address=addr)
        r = repr(u)
        assert "User" in r
        assert "id=1" in r
        assert "name='Alice'" in r


class TestEntityCopy:
    def test_copy_preserves_values(self) -> None:
        e = SimpleEntity(id=1, value="test")
        e2 = e.copy(value="changed")
        assert e2.id == 1
        assert e2.value == "changed"

    def test_copy_preserves_immutability(self) -> None:
        e = SimpleEntity(id=1, value="test")
        e2 = e.copy(value="changed")
        with pytest.raises(MutationForbiddenException):
            e2.value = "again"


class TestEntityEvents:
    def test_entity_emits_event(self) -> None:
        e = SimpleEntity(id=1, value="test")
        e._event_emitter.emit(UserCreated(user_id=1))
        events = e._event_emitter.poll_events()
        assert len(events) == 1
        assert isinstance(events[0], UserCreated)

    def test_entity_event_emitted_at_is_set(self) -> None:
        e = SimpleEntity(id=1, value="test")
        e._event_emitter.emit(UserCreated(user_id=1))
        events = e._event_emitter.poll_events()
        assert events[0].emitted_at is not None

    def test_entity_events_captured_by_collector(self) -> None:
        e = SimpleEntity(id=1, value="test")
        with EventCollector() as collector:
            e._event_emitter.emit(UserCreated(user_id=1))
            assert len(collector) == 1


class TestEntityEquality:
    def test_entity_fields_are_equal(self) -> None:
        e1 = SimpleEntity(id=1, value="test")
        e2 = SimpleEntity(id=1, value="test")
        assert e1.id == e2.id
        assert e1.value == e2.value

    def test_entity_different_values(self) -> None:
        e1 = SimpleEntity(id=1, value="a")
        e2 = SimpleEntity(id=2, value="b")
        assert e1.id != e2.id


class TestEntityEqualityWithEq:
    def test_entity_eq_same_id(self) -> None:
        e1 = SimpleEntity(id=1, value="a")
        e2 = SimpleEntity(id=1, value="b")
        assert e1 == e2

    def test_entity_eq_different_id(self) -> None:
        e1 = SimpleEntity(id=1, value="a")
        e2 = SimpleEntity(id=2, value="a")
        assert e1 != e2

    def test_entity_eq_different_type(self) -> None:
        class OtherEntity(Entity):
            id: int = Field(id=True)
            value: str

        e1 = SimpleEntity(id=1, value="a")
        e2 = OtherEntity(id=1, value="a")
        assert e1 != e2
        assert e2 != e1

    def test_entity_hash_dict_key(self) -> None:
        e1 = SimpleEntity(id=1, value="a")
        e2 = SimpleEntity(id=1, value="b")
        d = {e1: "first"}
        assert d[e2] == "first"

    def test_entity_hash_in_set(self) -> None:
        e1 = SimpleEntity(id=1, value="a")
        e2 = SimpleEntity(id=1, value="b")
        s = {e1, e2}
        assert len(s) == 1

    def test_entity_identity_property(self) -> None:
        e = SimpleEntity(id=42, value="test")
        assert e.__entity_id__ == 42
