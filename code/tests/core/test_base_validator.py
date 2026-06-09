import inspect
from typing import Annotated, Any, Callable, cast

import pytest
from aod._internal.core.base_validator import BaseValidator
from aod._internal.core.domain_exception import (
    InvarianceException,
    ModelValidationError,
    MutationForbiddenException,
)
from aod._internal.core.reconstructable import ReconstructMixin
from aod._internal.core.fields import Field, PrivateField
from aod._internal.core.fields.fields import Unset
from aod._internal.core.invariances import (
    AfterValidator,
    field_invariance,
    invariance,
)


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


def test_base_validator_field_invariance_runs() -> None:
    class User(BaseValidator):
        age: int

        @field_invariance("age")
        def normalize_age(cls, value: int) -> int:
            return value + 10

    user = User(age=5)

    assert user.age == 15


def test_base_validator_reconstruct_skips_field_validators() -> None:
    class User(ReconstructMixin, BaseValidator):
        age: Annotated[int, AfterValidator(lambda value: value + 10)]

    validated = User(age=5)
    raw = User.reconstruct(age=5)

    assert validated.age == 15
    assert raw.age == 5


def test_base_validator_supports_annotated_field_constraints() -> None:
    class User(BaseValidator):
        name: Annotated[str, Field(min_length=3)]

    user = User(name="alf")

    assert user.name == "alf"


def test_base_validator_annotated_field_constraints_raise_validation_error() -> None:
    class User(BaseValidator):
        name: Annotated[str, Field(min_length=3)]

    with pytest.raises(ModelValidationError):
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


def test_base_validator_private_field_default_factory_creates_unique_values() -> None:
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
    with pytest.raises(ModelValidationError):
        User(**kwargs)


# ---------------------------------------------------------------------------
# invariance
# ---------------------------------------------------------------------------


def test_invariance_runs_on_normal_construction() -> None:
    class User(BaseValidator):
        age: int
        label: str = ""

        @invariance
        def set_label(self) -> None:
            self.label = f"user:{self.age}"

    user = User(age=5)

    assert user.label == "user:5"


def test_invariance_does_not_run_on_reconstruct() -> None:
    """invariance must be skipped when reconstructing via reconstruct."""

    class User(ReconstructMixin, BaseValidator):
        age: int
        label: str = ""

        @invariance
        def set_label(self) -> None:
            self.label = f"user:{self.age}"

    user = User.reconstruct(age=7, label="")

    assert user.label == ""


def test_invariance_can_raise_validation_error() -> None:
    class User(BaseValidator):
        age: int

        @invariance
        def reject_minors(self) -> None:
            if self.age < 18:
                raise ValueError("Must be 18 or older")

    with pytest.raises(InvarianceException, match="Must be 18 or older"):
        User(age=16)


def test_invariance_with_parentheses_covers_lambda_branch() -> None:
    class User(BaseValidator):
        age: int

        @invariance()
        def reject_minors(self) -> None:
            if self.age < 18:
                raise ValueError("Must be 18 or older")

    with pytest.raises(InvarianceException, match="Must be 18 or older"):
        User(age=16)


def test_invariance_does_not_raise_on_reconstruct() -> None:
    """Since invariance is not in the raw model, reconstruct bypasses it."""

    class User(ReconstructMixin, BaseValidator):
        age: int

        @invariance
        def reject_minors(self) -> None:
            if self.age < 18:
                raise ValueError("Must be 18 or older")

    user = User.reconstruct(age=16)

    assert user.age == 16


def test_unset_repr() -> None:
    assert repr(Unset()) == "UNSET FIELD"


def test_child_inherits_field_invariance_from_parent() -> None:
    class Parent(BaseValidator):
        age: int

        @field_invariance("age")
        def normalize_age(cls, value: int) -> int:
            return value + 5

    class Child(Parent):
        pass

    child = Child(age=10)
    assert child.age == 15


def test_base_validator_accepts_dict_model_config() -> None:
    class DictConfig(BaseValidator):
        model_config = {"frozen": True}
        age: int

    obj = DictConfig(age=1)
    assert obj.age == 1


class _CopyModel(BaseValidator):
    name: str
    age: int = 0


def test_copy_without_overrides_returns_same_values() -> None:
    original = _CopyModel(name="Alice", age=30)
    copied = original.copy()
    assert copied.name == "Alice"
    assert copied.age == 30


def test_copy_original_unchanged() -> None:
    original = _CopyModel(name="Alice", age=30)
    copied = original.copy(age=99)
    assert original.age == 30
    assert copied.age == 99


def test_copy_runs_validation() -> None:
    original = _CopyModel(name="Alice", age=30)
    with pytest.raises(ModelValidationError):
        original.copy(age="not a number")


def test_copy_preserves_immutability() -> None:
    from aod._internal.core.base_sealed import BaseSealed

    class _SealedCopy(BaseSealed):
        name: str

    original = _SealedCopy(name="Alice")
    copied = original.copy(name="Bob")
    assert copied.name == "Bob"
    assert original.name == "Alice"
    with pytest.raises(MutationForbiddenException):
        copied.name = "Charlie"
