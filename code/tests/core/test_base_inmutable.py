from typing import Any, cast

import pytest
from aod._internal.core.base_immutable import BaseImmutable
from aod._internal.core.domain_exception import MutationForbiddenException


def test_base_immutable_blocks_mutation_after_init() -> None:
    class User(BaseImmutable):
        age: int

    user = User(age=1)

    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
        user.age = 5


def test_base_immutable_validates_input_on_construction() -> None:
    class User(BaseImmutable):
        age: int

    user = User(age=cast(Any, "9"))

    assert user.age == 9
