from __future__ import annotations

from typing import Generic, TypeVar

import pytest
from aod._internal.core.type_handlers.generic_utils import (
    get_last_generic_arg,
    validate_handler_subclass,
    validate_generic_arg_is_subclass,
)
from aod._internal.core.domain_exception import InvalidGenericTypeArgError

T = TypeVar("T")
U = TypeVar("U")


class Base(Generic[T]):
    pass


class Good(Base[int]):
    pass


class Bad(Base[str]):
    pass


class Unrelated:
    pass


class OtherBase(Generic[T, U]):
    pass


class MultiArg(OtherBase[int, str]):
    pass


class HandlerBase(Generic[T]):
    pass


class Command(Generic[T]):
    pass


class ValidHandler(HandlerBase[Command[int]]):
    pass


class TestGetLastGenericArg:
    def test_returns_last_arg(self) -> None:
        assert get_last_generic_arg(Good) is int

    def test_returns_last_of_multi(self) -> None:
        assert get_last_generic_arg(MultiArg) is str

    def test_no_orig_bases_returns_none(self) -> None:
        assert get_last_generic_arg(int) is None

    def test_no_type_args_returns_none(self) -> None:
        class Bare(Base):
            pass

        result = get_last_generic_arg(Bare)
        assert result is None or isinstance(result, TypeVar)


class TestValidateGenericArgIsSubclass:
    def test_passes_for_valid_arg(self) -> None:
        validate_generic_arg_is_subclass(Good, Base, int)

    def test_raises_for_invalid_arg(self) -> None:
        with pytest.raises(InvalidGenericTypeArgError):
            validate_generic_arg_is_subclass(Bad, Base, int)

    def test_skip_for_non_class(self) -> None:
        class TypeVarArg(Base[T]):
            pass

        validate_generic_arg_is_subclass(TypeVarArg, Base, int)


class TestValidateHandlerSubclass:
    def test_passes_for_valid_handler(self) -> None:
        validate_handler_subclass(ValidHandler, HandlerBase, int, arg_name="T")

    def test_no_orig_bases_does_not_raise(self) -> None:
        validate_handler_subclass(Unrelated, HandlerBase, int, arg_name="T")
