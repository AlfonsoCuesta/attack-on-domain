import pytest
from core.base_mutable import BaseMutable, MutatingContext, MutatingState


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


def test_base_mutable_blocks_direct_attribute_mutation() -> None:
    class User(BaseMutable):
        age: int

    user = User(age=1)

    with pytest.raises(ValueError, match="Cannot mutate this object"):
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

    with pytest.raises(ValueError, match="Cannot mutate this object"):
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
