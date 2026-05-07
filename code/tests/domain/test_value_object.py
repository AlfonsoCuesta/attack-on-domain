import pytest

from domain.value_object import ValueObject


def test_value_object_is_immutable_after_init() -> None:
    class Money(ValueObject):
        amount: int

    m = Money(amount=1)

    with pytest.raises(ValueError, match="Cannot mutate this object"):
        m.amount = 2

