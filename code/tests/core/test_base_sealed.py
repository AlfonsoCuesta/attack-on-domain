from typing import Any, cast

import pytest
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import MutationForbiddenException


def test_base_sealed_blocks_mutation_after_init() -> None:
    class User(BaseSealed):
        age: int

    user = User(age=1)

    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
        user.age = 5


def test_base_sealed_validates_input_on_construction() -> None:
    class User(BaseSealed):
        age: int

    user = User(age=cast(Any, "9"))

    assert user.age == 9
