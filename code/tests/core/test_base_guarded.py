from typing import Any, Literal

import pytest
from aod._internal.core.base_guarded import (
    BaseGuarded,
    MutatingContext,
    MutatingState,
    inherit_context,
)
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import MutationForbiddenException


def test_base_guarded_uses_same_mutating_context_across_inheritance_levels() -> None:
    events = []

    class RecordingContext(MutatingContext):
        def __init__(self) -> None:
            super().__init__()

        def enter(self, state: Literal[MutatingState.PASS, MutatingState.INHERIT]) -> None:
            events.append(("enter", state))
            super().enter(state)

        def exit(self, state: Literal[MutatingState.PASS, MutatingState.INHERIT]) -> None:
            events.append(("exit", state))
            super().exit(state)

    class Inner(BaseGuarded):
        __mutating_context_class__ = RecordingContext
        age: int

        def inner_set(self, value: int) -> None:
            self.age = value

    class Outer(Inner):
        def outer_set(self, value: int) -> None:
            self.inner_set(value)

    obj = Outer(age=1)
    obj.outer_set(2)
    obj.inner_set(3)
    assert events == [
        # __init__
        ("enter", MutatingState.INHERIT),
        ("exit", MutatingState.INHERIT),
        # outer_set calling
        ("enter", MutatingState.PASS),  # outer_set
        ("enter", MutatingState.PASS),  # inner_set
        ("enter", MutatingState.INHERIT),  # _can_mutate
        ("exit", MutatingState.INHERIT),  # _can_mutate
        ("exit", MutatingState.PASS),  # inner_set
        ("exit", MutatingState.PASS),  # outer_set
        # inner_set calling
        ("enter", MutatingState.PASS),  # inner_set
        ("enter", MutatingState.INHERIT),  # _can_mutate
        ("exit", MutatingState.INHERIT),  # _can_mutate
        ("exit", MutatingState.PASS),  # inner_set
    ]


def test_base_guarded_blocks_direct_attribute_mutation() -> None:
    class User(BaseGuarded):
        age: int

    user = User(age=1)

    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
        user.age = 3


def test_base_guarded_allows_mutation_inside_public_method() -> None:
    class User(BaseGuarded):
        age: int

        def set_age(self, value: int) -> None:
            self.age = value

    user = User(age=1)
    user.set_age(10)

    assert user.age == 10


def test_base_guarded_respects_can_mutate_for_public_methods() -> None:
    class User(BaseGuarded):
        age: int

        def _can_mutate(self) -> bool:
            return False

        def set_age(self, value: int) -> None:
            self.age = value

    user = User(age=1)

    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
        user.set_age(10)


def test_base_guarded_not_allows_inherit_mutate_in_private_methods() -> None:
    class User(BaseGuarded):
        age: int

        def _can_mutate(self) -> bool:
            return False

        def _force_set_age(self, value: int) -> None:
            self.age = value

    user = User(age=1)
    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object User"):
        user._force_set_age(20)


def test_base_guarded_nested_method_calls_keep_context() -> None:
    class User(BaseGuarded):
        age: int

        def set_age(self, value: int) -> None:
            self._set_age_internal(value)

        def _set_age_internal(self, value: int) -> None:
            self.age = value

    user = User(age=1)
    user.set_age(7)

    assert user.age == 7


def test_base_guarded_private_method_no_super() -> None:
    class User(BaseGuarded):
        age: int

        def _can_mutate(self) -> bool:
            return False

        def set_age(self, value: int) -> None:
            self.age = value

        def _set_age(self, value: int) -> None:
            self.age = value

    user = User(age=1)
    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object User"):
        user.set_age(7)

    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object User"):
        user._set_age(7)


def test_base_guarded_works_with_inherit_context() -> None:
    class User(BaseGuarded):
        age: int

        def _can_mutate(self) -> bool:
            return False

        def set_age(self, value: int) -> None:
            self.age = value

        @inherit_context
        def super_set_age(self, value: int) -> None:
            self.age = value

    user = User(age=1)
    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object User"):
        user.set_age(7)

    user.super_set_age(7)
    assert user.age == 7


# ---------------------------------------------------------------------------
# MutableObjectProxy — complex fields
# ---------------------------------------------------------------------------


def test_complex_field_list_mutation_blocked_when_cannot_mutate() -> None:
    class Bag(BaseGuarded):
        items: list = []

        def _can_mutate(self) -> bool:
            return False

        def add(self, item) -> None:
            self.items.append(item)

    bag = Bag()

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable list"):
        bag.add(1)


def test_complex_field_list_mutation_allowed_when_can_mutate() -> None:
    class Bag(BaseGuarded):
        items: list = []

        def add(self, item) -> None:
            self.items.append(item)

    bag = Bag()
    bag.add(1)

    assert bag.items == [1]


def test_complex_field_list_read_allowed_when_cannot_mutate() -> None:
    """Non-mutating calls on a complex field must not raise even if can_mutate is False."""

    class Bag(BaseGuarded):
        items: list = []

        def _can_mutate(self) -> bool:
            return False

        def count(self, item) -> int:
            return self.items.count(item)

    bag = Bag()

    assert bag.count(1) == 0


def test_complex_field_dict_mutation_blocked_when_cannot_mutate() -> None:
    class Store(BaseGuarded):
        data: dict = {}

        def _can_mutate(self) -> bool:
            return False

        def put(self, key, value) -> None:
            self.data[key] = value

    store = Store()

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable dict"):
        store.put("x", 1)


def test_complex_field_dict_mutation_allowed_when_can_mutate() -> None:
    class Store(BaseGuarded):
        data: dict = {}

        def put(self, key, value) -> None:
            self.data[key] = value

    store = Store()
    store.put("x", 1)

    assert store.data == {"x": 1}


def test_complex_field_set_mutation_blocked_when_cannot_mutate() -> None:
    class Tags(BaseGuarded):
        values: set = set()

        def _can_mutate(self) -> bool:
            return False

        def add(self, tag) -> None:
            self.values.add(tag)

    tags = Tags()

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable set"):
        tags.add("foo")


def test_complex_field_mutation_blocked_from_outside_when_cannot_mutate() -> None:
    """Mutation attempted directly from outside the class must also be blocked."""

    class Bag(BaseGuarded):
        items: list = []

        def _can_mutate(self) -> bool:
            return False

    bag = Bag()

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable list"):
        bag.items.append(1)


def test_complex_field_custom_object_mutation_blocked_when_cannot_mutate() -> None:
    """A custom object whose mutating method modifies internal state is also protected."""

    class Counter:
        def __init__(self):
            self.value = 0

        def increment(self):
            self.value += 1

        def get(self):
            return self.value

        def __eq__(self, other):
            return isinstance(other, Counter) and self.value == other.value

        def __copy__(self):
            c = Counter()
            c.value = self.value
            return c

    class Widget(BaseGuarded):
        counter: Counter

        def _can_mutate(self) -> bool:
            return False

        def tick(self) -> None:
            self.counter.increment()

    widget = Widget(counter=Counter())

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable object"):
        widget.tick()


def test_complex_field_custom_object_read_allowed_when_cannot_mutate() -> None:
    """A non-mutating method on a custom object must not raise."""

    class Counter:
        def __init__(self):
            self.value = 0

        def get(self):
            return self.value

        def __eq__(self, other):
            return isinstance(other, Counter) and self.value == other.value

        def __copy__(self):
            c = Counter()
            c.value = self.value
            return c

    class Widget(BaseGuarded):
        counter: Counter

        def _can_mutate(self) -> bool:
            return False

        def read(self) -> int:
            return self.counter.get()

    widget = Widget(counter=Counter())

    assert widget.read() == 0


# ---------------------------------------------------------------------------
# Nested BaseGuarded objects
# ---------------------------------------------------------------------------


def test_nested_base_guarded_allows_mutation_when_both_can_mutate() -> None:
    class Child(BaseGuarded):
        age: int

        def set_age(self, value: int) -> None:
            self.age = value

    class Parent(BaseGuarded):
        child: Child

        def set_child_age(self, value: int) -> None:
            self.child.set_age(value)

    parent = Parent(child=Child(age=1))
    parent.set_child_age(5)

    assert parent.child.age == 5


def test_nested_base_guarded_blocks_when_parent_cannot_mutate() -> None:
    class Child(BaseGuarded):
        age: int

        def set_age(self, value: int) -> None:
            self.age = value

    class Parent(BaseGuarded):
        child: Child

        def _can_mutate(self) -> bool:
            return False

        def set_child_age(self, value: int) -> None:
            self.child.set_age(value)

    parent = Parent(child=Child(age=1))

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable object"):
        parent.set_child_age(9)


def test_nested_base_guarded_blocks_when_only_child_cannot_mutate() -> None:
    class Child(BaseGuarded):
        age: int

        def _can_mutate(self) -> bool:
            return False

        def set_age(self, value: int) -> None:
            self.age = value

    class Parent(BaseGuarded):
        child: Child

        def set_child_age(self, value: int) -> None:
            self.child.set_age(value)

    parent = Parent(child=Child(age=1))

    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
        parent.set_child_age(9)


def test_nested_base_guarded_direct_external_mutation_blocked_when_parent_cannot_mutate() -> None:
    class Child(BaseGuarded):
        age: int

    class Parent(BaseGuarded):
        child: Child

        def _can_mutate(self) -> bool:
            return False

    parent = Parent(child=Child(age=1))

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable object"):
        parent.child.age = 8


def test_can_mutate_override_inherits_super_mutable_and_does_not_recurse() -> None:
    class NoMutationClass(BaseGuarded):
        data: int
        mutate: bool = False

        def change_data(self, value: int) -> None:
            self.data = value

        def _can_mutate(self) -> bool:
            return self.mutate

    no_mutation = NoMutationClass(data=1)
    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
        no_mutation.change_data(2)


def test_check_immutable_object_from_immutable_getattr() -> None:
    class ImmutableListItem(BaseGuarded):
        data: int

        def _can_mutate(self) -> bool:
            return False

    class ImmutableList(BaseGuarded):
        data_list: list[ImmutableListItem]

        def _can_mutate(self) -> bool:
            return False

    immutable_item = ImmutableListItem(data=1)
    immutable = ImmutableList(data_list=[immutable_item])
    assert immutable.data_list == [immutable_item]
    assert immutable.data_list.__class__.__name__ == "ImmutableList"
    assert immutable.data_list[0].__class__.__name__ == "ImmutableImmutableListItem"


def test_check_mutable_object_from_mutable_getattr() -> None:
    class ImmutableListItem(BaseGuarded):
        data: int

        def _can_mutate(self) -> bool:
            return False

    class MutableList(BaseGuarded):
        data_list: list[ImmutableListItem]

        def get_data_list(self) -> list[ImmutableListItem]:
            return self.data_list

    immutable_item = ImmutableListItem(data=1)
    mutable = MutableList(data_list=[immutable_item])
    assert mutable.data_list == [immutable_item]
    assert mutable.data_list.__class__.__name__ == "ImmutableList"
    assert mutable.data_list[0].__class__.__name__ == "ImmutableImmutableListItem"
    assert mutable.get_data_list() == [immutable_item]
    assert mutable.get_data_list().__class__ is list
    assert mutable.get_data_list()[0].__class__.__name__ == "ImmutableListItem"


def test_base_sealed_can_mutate_returns_false() -> None:
    class Sealed(BaseSealed):
        value: int

    obj = Sealed(value=42)
    assert obj._can_mutate() is False


def test_delattr_inside_public_method() -> None:
    class User(BaseGuarded):
        name: str
        age: int

        def delete_age(self) -> None:
            del self.age

    user = User(name="alice", age=30)
    user.delete_age()
    assert not hasattr(user, "age")


def test_getattr_returns_function_field_as_is_when_cannot_mutate() -> None:
    def my_func() -> str:
        return "hello"

    class Container(BaseGuarded):
        fn: Any

        def _can_mutate(self) -> bool:
            return False

    obj = Container(fn=my_func)
    assert obj.fn is my_func
    assert callable(obj.fn)
    assert obj.fn() == "hello"
