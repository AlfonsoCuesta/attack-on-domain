from typing import Optional

import pytest
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.core.fields import Field
from aod._internal.domain.value_object import ValueObject


def test_value_object_is_immutable_after_init() -> None:
    class Money(ValueObject):
        amount: int

    m = Money(amount=1)

    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
        m.amount = 2


def test_check_no_cache_immutable_object() -> None:
    class RelativePoint(ValueObject):
        x: float = Field(ge=0, le=100)
        y: float = Field(ge=0, le=100)

    class Clickable(ValueObject):
        interest_point: Optional[RelativePoint] = Field(
            default_factory=lambda: RelativePoint(x=50, y=50)
        )

    interest_point = RelativePoint(x=25, y=75)

    clickable = Clickable(
        interest_point=interest_point,
    )

    assert clickable.interest_point == interest_point
