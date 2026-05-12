from typing import Any, cast

import pytest
from deedee._internal.core.base_inmutable import BaseInmutable
from deedee._internal.core.domain_exception import MutationForbiddenError


def test_base_inmutable_blocks_mutation_after_init() -> None:
    class User(BaseInmutable):
        age: int

    user = User(age=1)

    with pytest.raises(
        MutationForbiddenError, match="Cannot mutate this object"
    ):
        user.age = 5


def test_base_inmutable_sets_initialized_flag() -> None:
    class User(BaseInmutable):
        age: int

    user = User(age=1)

    assert user.__initialized__ is True


def test_base_inmutable_validates_input_on_construction() -> None:
    class User(BaseInmutable):
        age: int

    user = User(age=cast(Any, "9"))

    assert user.age == 9
