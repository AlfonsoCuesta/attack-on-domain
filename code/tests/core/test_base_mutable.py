from typing import Literal, cast

import pytest
from core.base_mutable import BaseMutable, MutatingContext, MutatingState
from core.domain_exception import MutationForbiddenError


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


def test_base_mutable_uses_same_mutating_context_across_inheritance_levels() -> (
    None
):
    class RecordingContext(MutatingContext):
        def __init__(self) -> None:
            super().__init__()
            self.events: list[tuple[str, MutatingState]] = []

        def enter(
            self, state: Literal[MutatingState.PASS, MutatingState.SUPER]
        ) -> None:
            self.events.append(("enter", state))
            super().enter(state)

        def exit(
            self, state: Literal[MutatingState.PASS, MutatingState.SUPER]
        ) -> None:
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
        ("exit", MutatingState.PASS),  # inner_set
        ("exit", MutatingState.PASS),  # outer_set
        ("enter", MutatingState.PASS),  # inner_set (direct)
        ("exit", MutatingState.PASS),  # inner_set (direct)
    ]


def test_base_mutable_blocks_direct_attribute_mutation() -> None:
    class User(BaseMutable):
        age: int

    user = User(age=1)

    with pytest.raises(MutationForbiddenError, match="Cannot mutate this object"):
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

        def can_mutate(self) -> bool:
            return False

        def set_age(self, value: int) -> None:
            self.age = value

    user = User(age=1)

    with pytest.raises(MutationForbiddenError, match="Cannot mutate this object"):
        user.set_age(10)


def test_base_mutable_allows_super_mutate_in_private_methods() -> None:
    class User(BaseMutable):
        age: int

        def can_mutate(self) -> bool:
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
