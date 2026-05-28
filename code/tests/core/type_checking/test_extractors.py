from typing import Optional

from aod._internal.core.type_checking.extractors import (
    extract_types_from_annotation,
    get_validation_model,
)


def test_extract_types_from_plain_class() -> None:
    class User:
        pass

    assert extract_types_from_annotation(User) == [User]


def test_extract_types_from_optional() -> None:
    class User:
        pass

    result = extract_types_from_annotation(Optional[User])
    assert User in result


def test_extract_types_from_list() -> None:
    class User:
        pass

    result = extract_types_from_annotation(list[User])
    assert User in result


def test_extract_types_from_union() -> None:
    class A:
        pass

    class B:
        pass

    result = extract_types_from_annotation(A | B)
    assert A in result
    assert B in result


def test_extract_types_from_string_returns_empty() -> None:
    assert extract_types_from_annotation("User") == []


def test_extract_types_from_primitive() -> None:
    assert extract_types_from_annotation(int) == [int]


def test_extract_types_from_none_type() -> None:
    assert extract_types_from_annotation(type(None)) == [type(None)]


def test_get_validation_model_on_base_validator() -> None:
    from aod._internal.core.base_validator import BaseValidator

    class User(BaseValidator):
        name: str
        age: int

    model = get_validation_model(User)

    assert model.__name__ == "UserValidationModel"
    assert "name" in model.model_fields
    assert "age" in model.model_fields
