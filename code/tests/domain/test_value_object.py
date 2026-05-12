import pytest
from deedee._internal.core.domain_exception import MutationForbiddenError
from deedee._internal.domain.value_object import ValueObject


def test_value_object_is_immutable_after_init() -> None:
    class Money(ValueObject):
        amount: int

    m = Money(amount=1)

    with pytest.raises(
        MutationForbiddenError, match="Cannot mutate this object"
    ):
        m.amount = 2
