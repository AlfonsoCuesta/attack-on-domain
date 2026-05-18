from typing import Literal, cast

import pytest
from aod._internal.core.base_mutable import (
    BaseMutable,
    MutatingContext,
    MutatingState,
)
from aod._internal.core.domain_exception import MutationForbiddenException


def test_mutating_context_state_transitions() -> None:
    ctx = MutatingContext()
    assert ctx.status == MutatingState.BLOCK

    ctx.enter(MutatingState.PASS)
    assert ctx.status == MutatingState.PASS

    ctx.enter(MutatingState.SUPER)
    assert ctx.status == MutatingState.SUPER

    ctx.exit(MutatingState.SUPER)
    assert ctx.status == MutatingState.PASS

    ctx.exit(MutatingState.PASS)
    assert ctx.status == MutatingState.BLOCK


def test_base_mutable_uses_same_mutating_context_across_inheritance_levels() -> None:
    class RecordingContext(MutatingContext):
        def __init__(self) -> None:
            super().__init__()
            self.events: list[tuple[str, MutatingState]] = []

        def enter(
            self, state: Literal[MutatingState.PASS, MutatingState.SUPER]
        ) -> None:
            self.events.append(("enter", state))
            super().enter(state)

        def exit(self, state: Literal[MutatingState.PASS, MutatingState.SUPER]) -> None:
            self.events.append(("exit", state))
            super().exit(state)

    class Inner(BaseMutable):
        __mutating_context_class__ = RecordingContext
        age: int

        def inner_set(self, value: int) -> None:
            self.age = value

    class Outer(Inner):
        def outer_set(self, value: int) -> None:
            self.inner_set(value)

    obj = Outer(age=1)
    ctx_before = obj._get_mutating_context()

    obj.outer_set(2)
    obj.inner_set(3)

    ctx_after = cast(RecordingContext, obj._get_mutating_context())
    assert ctx_before is ctx_after

    assert ctx_after.events == [
        ("enter", MutatingState.SUPER),  # _set_attributes
        ("exit", MutatingState.SUPER),  # _set_attributes
        ("enter", MutatingState.PASS),  # outer_set
        ("enter", MutatingState.PASS),  # inner_set (nested)
        ("enter", MutatingState.SUPER),  # _can_mutate check inside __setattr__
        ("exit", MutatingState.SUPER),  # _can_mutate check inside __setattr__
        ("exit", MutatingState.PASS),  # inner_set
        ("exit", MutatingState.PASS),  # outer_set
        ("enter", MutatingState.PASS),  # inner_set (direct)
        ("enter", MutatingState.SUPER),  # _can_mutate check inside __setattr__
        ("exit", MutatingState.SUPER),  # _can_mutate check inside __setattr__
        ("exit", MutatingState.PASS),  # inner_set (direct)
    ]


def test_base_mutable_blocks_direct_attribute_mutation() -> None:
    class User(BaseMutable):
        age: int

    user = User(age=1)

    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
        user.age = 3


def test_base_mutable_allows_mutation_inside_public_method() -> None:
    class User(BaseMutable):
        age: int

        def set_age(self, value: int) -> None:
            self.age = value

    user = User(age=1)
    user.set_age(10)

    assert user.age == 10


def test_base_mutable_respects_can_mutate_for_public_methods() -> None:
    class User(BaseMutable):
        age: int

        def _can_mutate(self) -> bool:
            return False

        def set_age(self, value: int) -> None:
            self.age = value

    user = User(age=1)

    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
        user.set_age(10)


def test_base_mutable_allows_super_mutate_in_private_methods() -> None:
    class User(BaseMutable):
        age: int

        def _can_mutate(self) -> bool:
            return False

        def _force_set_age(self, value: int) -> None:
            self.age = value

    user = User(age=1)
    user._force_set_age(20)

    assert user.age == 20


def test_base_mutable_nested_method_calls_keep_context() -> None:
    class User(BaseMutable):
        age: int

        def set_age(self, value: int) -> None:
            self._set_age_internal(value)

        def _set_age_internal(self, value: int) -> None:
            self.age = value

    user = User(age=1)
    user.set_age(7)

    assert user.age == 7


# ---------------------------------------------------------------------------
# MutableObjectProxy — complex fields
# ---------------------------------------------------------------------------


def test_complex_field_list_mutation_blocked_when_cannot_mutate() -> None:
    class Bag(BaseMutable):
        items: list = []

        def _can_mutate(self) -> bool:
            return False

        def add(self, item) -> None:
            self.items.append(item)

    bag = Bag()

    with pytest.raises(
        MutationForbiddenException, match="Cannot modify an immutable list"
    ):
        bag.add(1)


def test_complex_field_list_mutation_allowed_when_can_mutate() -> None:
    class Bag(BaseMutable):
        items: list = []

        def add(self, item) -> None:
            self.items.append(item)

    bag = Bag()
    bag.add(1)

    assert bag.items == [1]


def test_complex_field_list_read_allowed_when_cannot_mutate() -> None:
    """Non-mutating calls on a complex field must not raise even if can_mutate is False."""

    class Bag(BaseMutable):
        items: list = []

        def _can_mutate(self) -> bool:
            return False

        def count(self, item) -> int:
            return self.items.count(item)

    bag = Bag()

    assert bag.count(1) == 0


def test_complex_field_dict_mutation_blocked_when_cannot_mutate() -> None:
    class Store(BaseMutable):
        data: dict = {}

        def _can_mutate(self) -> bool:
            return False

        def put(self, key, value) -> None:
            self.data[key] = value

    store = Store()

    with pytest.raises(
        MutationForbiddenException, match="Cannot modify an immutable dict"
    ):
        store.put("x", 1)


def test_complex_field_dict_mutation_allowed_when_can_mutate() -> None:
    class Store(BaseMutable):
        data: dict = {}

        def put(self, key, value) -> None:
            self.data[key] = value

    store = Store()
    store.put("x", 1)

    assert store.data == {"x": 1}


def test_complex_field_set_mutation_blocked_when_cannot_mutate() -> None:
    class Tags(BaseMutable):
        values: set = set()

        def _can_mutate(self) -> bool:
            return False

        def add(self, tag) -> None:
            self.values.add(tag)

    tags = Tags()

    with pytest.raises(
        MutationForbiddenException, match="Cannot modify an immutable set"
    ):
        tags.add("foo")


def test_complex_field_mutation_blocked_from_outside_when_cannot_mutate() -> None:
    """Mutation attempted directly from outside the class must also be blocked."""

    class Bag(BaseMutable):
        items: list = []

        def _can_mutate(self) -> bool:
            return False

    bag = Bag()

    with pytest.raises(
        MutationForbiddenException, match="Cannot modify an immutable list"
    ):
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

    class Widget(BaseMutable):
        counter: Counter

        def _can_mutate(self) -> bool:
            return False

        def tick(self) -> None:
            self.counter.increment()

    widget = Widget(counter=Counter())

    with pytest.raises(
        MutationForbiddenException, match="Cannot modify an immutable object"
    ):
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

    class Widget(BaseMutable):
        counter: Counter

        def _can_mutate(self) -> bool:
            return False

        def read(self) -> int:
            return self.counter.get()

    widget = Widget(counter=Counter())

    assert widget.read() == 0


# ---------------------------------------------------------------------------
# Nested BaseMutable objects
# ---------------------------------------------------------------------------


def test_nested_base_mutable_allows_mutation_when_both_can_mutate() -> None:
    class Child(BaseMutable):
        age: int

        def set_age(self, value: int) -> None:
            self.age = value

    class Parent(BaseMutable):
        child: Child

        def set_child_age(self, value: int) -> None:
            self.child.set_age(value)

    parent = Parent(child=Child(age=1))
    parent.set_child_age(5)

    assert parent.child.age == 5


def test_nested_base_mutable_blocks_when_parent_cannot_mutate() -> None:
    class Child(BaseMutable):
        age: int

        def set_age(self, value: int) -> None:
            self.age = value

    class Parent(BaseMutable):
        child: Child

        def _can_mutate(self) -> bool:
            return False

        def set_child_age(self, value: int) -> None:
            self.child.set_age(value)

    parent = Parent(child=Child(age=1))

    with pytest.raises(
        MutationForbiddenException, match="Cannot modify an immutable object"
    ):
        parent.set_child_age(9)


def test_nested_base_mutable_blocks_when_only_child_cannot_mutate() -> None:
    class Child(BaseMutable):
        age: int

        def _can_mutate(self) -> bool:
            return False

        def set_age(self, value: int) -> None:
            self.age = value

    class Parent(BaseMutable):
        child: Child

        def set_child_age(self, value: int) -> None:
            self.child.set_age(value)

    parent = Parent(child=Child(age=1))

    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
        parent.set_child_age(9)


def test_nested_base_mutable_direct_external_mutation_blocked_when_parent_cannot_mutate() -> (
    None
):
    class Child(BaseMutable):
        age: int

    class Parent(BaseMutable):
        child: Child

        def _can_mutate(self) -> bool:
            return False

    parent = Parent(child=Child(age=1))

    with pytest.raises(
        MutationForbiddenException, match="Cannot modify an immutable object"
    ):
        parent.child.age = 8


def test_can_mutate_accessor_does_not_recurse_infinitely() -> None:
    class NoMutationClass(BaseMutable):
        data: int
        mutate: bool = False

        def change_data(self, value: int) -> None:
            self.data = value

        def _can_mutate(self) -> bool:
            return self.mutate

    no_mutation = NoMutationClass(data=1)
    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
        no_mutation.change_data(2)
