"""Tests for BaseSealed class."""

from __future__ import annotations


import pytest

from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.core.fields import PrivateField


class SealedWithDefaults(BaseSealed):
    name: str
    count: int = 0
    label: str = "default"


class SealedWithPrivate(BaseSealed):
    name: str
    _secret: str = PrivateField(default="hidden")


class SealedChild(SealedWithDefaults):
    extra: str


class TestBaseSealedConstruction:
    def test_basic_construction(self) -> None:
        s = BaseSealed()
        assert s is not None

    def test_sealed_with_fields(self) -> None:
        s = SealedWithDefaults(name="test")
        assert s.name == "test"
        assert s.count == 0
        assert s.label == "default"

    def test_sealed_with_all_fields(self) -> None:
        s = SealedWithDefaults(name="test", count=5, label="custom")
        assert s.name == "test"
        assert s.count == 5
        assert s.label == "custom"

    def test_type_coercion(self) -> None:
        s = SealedWithDefaults(name="test", count="42")
        assert s.count == 42
        assert isinstance(s.count, int)

    def test_sealed_with_private_field(self) -> None:
        s = SealedWithPrivate(name="test")
        assert s.name == "test"
        assert s._secret == "hidden"

    def test_sealed_inheritance(self) -> None:
        s = SealedChild(name="parent", extra="child")
        assert s.name == "parent"
        assert s.extra == "child"
        assert s.count == 0


class TestBaseSealedImmutability:
    def test_blocks_attribute_mutation(self) -> None:
        s = SealedWithDefaults(name="test")
        with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
            s.name = "changed"

    def test_blocks_int_mutation(self) -> None:
        s = SealedWithDefaults(name="test", count=5)
        with pytest.raises(MutationForbiddenException):
            s.count = 10

    def test_blocks_default_field_mutation(self) -> None:
        s = SealedWithDefaults(name="test")
        with pytest.raises(MutationForbiddenException):
            s.label = "changed"

    def test_blocks_private_field_mutation(self) -> None:
        s = SealedWithPrivate(name="test")
        with pytest.raises(MutationForbiddenException):
            s._secret = "new secret"

    def test_child_sealed_blocks_mutation(self) -> None:
        s = SealedChild(name="parent", extra="child")
        with pytest.raises(MutationForbiddenException):
            s.extra = "changed"


class TestBaseSealedCopy:
    def test_copy_preserves_values(self) -> None:
        s = SealedWithDefaults(name="test", count=5)
        s2 = s.copy(count=10)
        assert s2.name == "test"
        assert s2.count == 10

    def test_copy_preserves_immutability(self) -> None:
        s = SealedWithDefaults(name="test")
        s2 = s.copy(count=5)
        with pytest.raises(MutationForbiddenException):
            s2.count = 10


class TestBaseSealedRepr:
    def test_repr(self) -> None:
        s = SealedWithDefaults(name="test", count=5)
        r = repr(s)
        assert "SealedWithDefaults" in r
        assert "name='test'" in r
        assert "count=5" in r
