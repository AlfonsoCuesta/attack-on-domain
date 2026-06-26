from __future__ import annotations

import pytest
from aod._internal.core.base_guarded import inherit_context
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.domain.entity import RootEntity
from aod._internal.domain.entity_id import EntityId
from aod._internal.domain.value_object import ValueObject


class StrId(EntityId):
    value: str


# ---------------------------------------------------------------------------
# Mutation scenarios
# ---------------------------------------------------------------------------


class MutableEntity(RootEntity):
    id: StrId = Field(id=True)
    name: str
    counter: int = 0

    def increment(self) -> None:
        self.counter += 1

    def rename(self, new_name: str) -> None:
        self.name = new_name


class GuardedEntity(RootEntity):
    id: StrId = Field(id=True)
    value: int = 0
    _allow_mutation: bool = PrivateField(default=False)

    def _can_mutate(self) -> bool:
        return self._allow_mutation

    def set_value(self, v: int) -> None:
        self.value = v

    def allow_mutation(self) -> None:
        object.__setattr__(self, "_allow_mutation", True)

    @inherit_context
    def force_set_value(self, v: int) -> None:
        self.value = v


class ImmutableValueObject(ValueObject):
    x: int
    y: int


class ParentEntity(RootEntity):
    id: StrId = Field(id=True)
    child: MutableEntity | None = None

    def set_child_name(self, name: str) -> None:
        if self.child is not None:
            self.child.rename(name)


class SealedValue(BaseSealed):
    data: int


# ===========================================================================
# TESTS
# ===========================================================================


class TestBasicMutation:
    def test_mutation_allowed_inside_public_method(self) -> None:
        e = MutableEntity(id=StrId(value="1"), name="Alice")
        e.increment()
        assert e.counter == 1

    def test_mutation_blocked_from_outside(self) -> None:
        e = MutableEntity(id=StrId(value="1"), name="Alice")
        with pytest.raises(MutationForbiddenException):
            e.name = "Bob"

    def test_mutation_blocked_on_value_object(self) -> None:
        v = ImmutableValueObject(x=1, y=2)
        with pytest.raises(MutationForbiddenException):
            v.x = 99

    def test_mutation_blocked_on_base_sealed(self) -> None:
        s = SealedValue(data=42)
        with pytest.raises(MutationForbiddenException):
            s.data = 0

    def test_delattr_blocked_from_outside(self) -> None:
        e = MutableEntity(id=StrId(value="1"), name="Alice")
        with pytest.raises(MutationForbiddenException):
            del e.name

    def test_delattr_allowed_inside_public_method(self) -> None:
        class WithDelete(RootEntity):
            id: StrId = Field(id=True)
            name: str

            def remove_name(self) -> None:
                del self.name

        e = WithDelete(id=StrId(value="1"), name="Alice")
        e.remove_name()
        assert not hasattr(e, "name")


class TestCanMutateOverride:
    def test_mutation_blocked_when_can_mutate_returns_false(self) -> None:
        e = GuardedEntity(id=StrId(value="1"))
        with pytest.raises(MutationForbiddenException):
            e.set_value(42)

    def test_mutation_allowed_when_can_mutate_returns_true(self) -> None:
        e = GuardedEntity(id=StrId(value="1"))
        e.allow_mutation()
        e.set_value(42)
        assert e.value == 42

    def test_inherit_context_bypasses_can_mutate(self) -> None:
        e = GuardedEntity(id=StrId(value="1"))
        e.force_set_value(42)
        assert e.value == 42

    def test_can_mutate_checked_on_every_call(self) -> None:
        e = GuardedEntity(id=StrId(value="1"))
        with pytest.raises(MutationForbiddenException):
            e.set_value(1)
        e.allow_mutation()
        e.set_value(2)
        assert e.value == 2


class TestNestedMutation:
    def test_nested_entity_mutation_allowed_inside_method(self) -> None:
        child = MutableEntity(id=StrId(value="c1"), name="Child")
        parent = ParentEntity(id=StrId(value="p1"), child=child)
        parent.set_child_name("Renamed")
        assert parent.child is not None
        assert parent.child.name == "Renamed"

    def test_nested_entity_mutation_blocked_from_outside(self) -> None:
        child = MutableEntity(id=StrId(value="c1"), name="Child")
        parent = ParentEntity(id=StrId(value="p1"), child=child)
        assert parent.child is not None
        with pytest.raises(MutationForbiddenException):
            parent.child.name = "Hacked"

    def test_nested_entity_immutable_proxy_outside_method(self) -> None:
        child = MutableEntity(id=StrId(value="c1"), name="Child")
        parent = ParentEntity(id=StrId(value="p1"), child=child)
        proxy = parent.child
        assert proxy.__class__.__name__.startswith("Immutable")

    def test_mutable_inside_method_not_proxied(self) -> None:
        child = MutableEntity(id=StrId(value="c1"), name="Child")
        parent = ParentEntity(id=StrId(value="p1"), child=child)
        parent.set_child_name("NewName")
        assert parent.child is not None
        assert parent.child.name == "NewName"


class TestImmutableProxies:
    def test_list_is_immutable_outside(self) -> None:
        class WithList(RootEntity):
            id: StrId = Field(id=True)
            items: list[int] = []

            def add(self, v: int) -> None:
                self.items.append(v)

        e = WithList(id=StrId(value="1"))
        proxy = e.items
        with pytest.raises(MutationForbiddenException):
            proxy.append(1)

    def test_list_mutable_inside_method(self) -> None:
        class WithList(RootEntity):
            id: StrId = Field(id=True)
            items: list[int] = []

            def add(self, v: int) -> None:
                self.items.append(v)

        e = WithList(id=StrId(value="1"))
        e.add(1)
        e.add(2)
        assert list(e.items) == [1, 2]

    def test_dict_is_immutable_outside(self) -> None:
        class WithDict(RootEntity):
            id: StrId = Field(id=True)
            data: dict[str, int] = {}

        e = WithDict(id=StrId(value="1"))
        proxy = e.data
        with pytest.raises(MutationForbiddenException):
            proxy["x"] = 1

    def test_set_is_immutable_outside(self) -> None:
        class WithSet(RootEntity):
            id: StrId = Field(id=True)
            tags: set[str] = set()

        e = WithSet(id=StrId(value="1"))
        proxy = e.tags
        with pytest.raises(MutationForbiddenException):
            proxy.add("x")


class TestEntitySpecific:
    def test_entity_can_mutate_inside_method(self) -> None:
        e = MutableEntity(id=StrId(value="1"), name="Alice")
        e.rename("Bob")
        assert e.name == "Bob"

    def test_entity_cannot_mutate_from_outside(self) -> None:
        e = MutableEntity(id=StrId(value="1"), name="Alice")
        with pytest.raises(MutationForbiddenException):
            e.id = StrId(value="2")

    def test_value_object_always_immutable(self) -> None:
        v = ImmutableValueObject(x=1, y=2)
        with pytest.raises(MutationForbiddenException):
            v.x = 3

    def test_base_sealed_always_immutable(self) -> None:
        s = SealedValue(data=42)
        with pytest.raises(MutationForbiddenException):
            s.data = 0
