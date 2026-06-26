from __future__ import annotations

from aod._internal.core.domain_exception import NoEntityIdException, TooManyEntityIdsException
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.entity_id import EntityId
from aod._internal.domain.value_object import ValueObject


class UserId(EntityId):
    value: str


class OtherId(EntityId):
    key: str


class TestEntityRequiresEntityId:
    def test_entity_without_entity_id_raises_at_runtime(self) -> None:
        class BadEntity(Entity):
            name: str

        b = BadEntity(name="foo")
        try:
            _ = b.__entity_id__
            assert False, "should have raised NoEntityIdException"
        except NoEntityIdException:
            pass

    def test_root_entity_without_entity_id_raises_at_runtime(self) -> None:
        class BadRoot(RootEntity):
            name: str

        b = BadRoot(name="foo")
        try:
            _ = b.__entity_id__
            assert False, "should have raised NoEntityIdException"
        except NoEntityIdException:
            pass

    def test_entity_with_multiple_entity_ids_raises_at_runtime(self) -> None:
        class BadEntity(Entity):
            id1: UserId
            id2: OtherId

        b = BadEntity(id1=UserId(value="a"), id2=OtherId(key="b"))
        try:
            _ = b.__entity_id__
            assert False, "should have raised TooManyEntityIdsException"
        except TooManyEntityIdsException:
            pass


class TestEntityIdFieldDetection:
    def test_single_entity_id_detected(self) -> None:
        class GoodEntity(Entity):
            id: UserId
            name: str

        assert GoodEntity(id=UserId(value="x"), name="test").__entity_id_field_name__ == "id"

    def test_root_entity_single_entity_id_detected(self) -> None:
        class GoodRoot(RootEntity):
            entity_id: UserId
            data: str

        assert (
            GoodRoot(entity_id=UserId(value="x"), data="test").__entity_id_field_name__
            == "entity_id"
        )


class TestEntityIdProperty:
    def test_property_returns_entity_id_value(self) -> None:
        class User(Entity):
            id: UserId
            name: str

        uid = UserId(value="abc")
        u = User(id=uid, name="test")
        assert u.__entity_id__ is uid

    def test_root_entity_id_property(self) -> None:
        class Admin(RootEntity):
            eid: UserId
            role: str

        uid = UserId(value="admin-1")
        a = Admin(eid=uid, role="super")
        assert a.__entity_id__ is uid


class TestEntityEqByEntityId:
    def test_same_entity_id_equals(self) -> None:
        class User(Entity):
            id: UserId
            name: str

        uid = UserId(value="abc")
        u1 = User(id=uid, name="alice")
        u2 = User(id=uid, name="bob")

        assert u1 == u2
        assert hash(u1) == hash(u2)

    def test_different_entity_id_not_equal(self) -> None:
        class User(Entity):
            id: UserId
            name: str

        u1 = User(id=UserId(value="a"), name="alice")
        u2 = User(id=UserId(value="b"), name="alice")

        assert u1 != u2

    def test_different_types_not_equal(self) -> None:
        class User(Entity):
            id: UserId
            name: str

        class Admin(Entity):
            id: OtherId
            role: str

        u = User(id=UserId(value="1"), name="x")
        a = Admin(id=OtherId(key="1"), role="x")

        assert u != a

    def test_self_equality(self) -> None:
        class User(Entity):
            id: UserId
            name: str

        u = User(id=UserId(value="x"), name="test")
        assert u == u


class TestEntityHash:
    def test_equal_entities_have_same_hash(self) -> None:
        class User(Entity):
            id: UserId
            name: str

        uid = UserId(value="same")
        assert hash(User(id=uid, name="a")) == hash(User(id=uid, name="b"))
        assert User(id=uid, name="a") == User(id=uid, name="b")
        assert {User(id=uid, name="a"), User(id=uid, name="b")} == {User(id=uid, name="b")}


class TestEntityIdValueObjectStillWorks:
    def test_can_use_value_object_as_before(self) -> None:
        class Money(ValueObject):
            amount: float

        m1 = Money(amount=10.0)
        m2 = Money(amount=10.0)
        assert m1 == m2
