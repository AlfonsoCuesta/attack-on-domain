import inspect
from typing import Annotated, Any, Callable, cast

import pytest
from aod._internal.core.base_validator import BaseValidator
from aod._internal.core.fields import Field, PrivateField
from aod._internal.core.validators import AfterValidator, field_validator
from pydantic import ValidationError


def test_base_validator_validates_and_sets_attributes() -> None:
    class User(BaseValidator):
        age: int
        name: str

    user = User(age=cast(Any, "12"), name="alf")

    assert user.age == 12
    assert user.name == "alf"


def test_base_validator_repr_uses_model_fields() -> None:
    class User(BaseValidator):
        age: int
        active: bool = False

    user = User(age=30)

    assert repr(user) == "User(age=30, active=False)"


def test_base_validator_field_validator_runs() -> None:
    class User(BaseValidator):
        age: int

        @field_validator("age")
        def normalize_age(cls, value: int) -> int:
            return value + 10

    user = User(age=5)

    assert user.age == 15


def test_base_validator_from_existing_skips_field_validators() -> None:
    class User(BaseValidator):
        age: Annotated[int, AfterValidator(lambda value: value + 10)]

    validated = User(age=5)
    raw = User.from_existing(age=5)

    assert validated.age == 15
    assert raw.age == 5


def test_base_validator_supports_annotated_field_constraints() -> None:
    class User(BaseValidator):
        name: Annotated[str, Field(min_length=3)]

    user = User(name="alf")

    assert user.name == "alf"


def test_base_validator_annotated_field_constraints_raise_validation_error() -> (
    None
):
    class User(BaseValidator):
        name: Annotated[str, Field(min_length=3)]

    with pytest.raises(ValidationError):
        User(name="ab")


def test_base_validator_allows_arbitrary_types() -> None:
    class CustomType:
        def __init__(self, value: int) -> None:
            self.value = value

    class User(BaseValidator):
        payload: CustomType

    payload = CustomType(3)
    user = User(payload=payload)

    assert user.payload is payload


def test_base_validator_sets_private_field_default_value() -> None:
    class User(BaseValidator):
        age: int
        _token: str = PrivateField(default="secret")

    user = User(age=1)

    assert user._token == "secret"


def test_base_validator_private_field_default_factory_creates_unique_values() -> (
    None
):
    class User(BaseValidator):
        age: int
        _tags: list[str] = PrivateField(default_factory=list)

    first = User(age=1)
    second = User(age=2)
    first._tags.append("x")

    assert first._tags == ["x"]
    assert second._tags == []


def test_private_field_rejects_init_argument() -> None:
    private_field_dynamic = cast(Callable[..., Any], PrivateField)
    with pytest.raises(TypeError):
        private_field_dynamic(init=True)


def test_base_validator_signature_matches_declared_fields() -> None:
    class User(BaseValidator):
        age: int
        name: str

    signature = inspect.signature(User.__init__)

    assert "age" in signature.parameters
    assert "name" in signature.parameters
    assert signature.parameters["age"].kind is inspect.Parameter.KEYWORD_ONLY


def test_base_validator_raises_when_required_field_is_missing() -> None:
    class User(BaseValidator):
        age: int
        name: str

    kwargs: dict[str, Any] = {"age": 1}
    with pytest.raises(ValidationError):
        User(**kwargs)
