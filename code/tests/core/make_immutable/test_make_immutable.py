from __future__ import annotations

import datetime
import decimal
import uuid
from copy import copy

import pytest
from aod._internal.core.base_guarded.make_immutable.immutable_custom import (
    _immutable_cache,
)
from aod._internal.core.base_guarded.make_immutable.immutable_dict import ImmutableDict
from aod._internal.core.base_guarded.make_immutable.immutable_list import ImmutableList
from aod._internal.core.base_guarded.make_immutable.immutable_set import ImmutableSet
from aod._internal.core.base_guarded.make_immutable.make_immutable import make_immutable
from aod._internal.core.base_guarded.make_immutable.wrapped_methods import (
    get_wrapped_methods,
)
from aod._internal.core.domain_exception import MutationForbiddenException


@pytest.mark.parametrize(
    "value",
    [
        1,
        1.5,
        "hola",
        True,
        b"bytes",
        None,
    ],
)
def test_make_immutable_returns_primitives_unchanged(value) -> None:
    assert make_immutable(value) is value


def test_make_immutable_returns_function_unchanged() -> None:
    def fn(x: int) -> int:
        return x + 1

    assert make_immutable(fn) is fn


def test_make_immutable_returns_bound_method_unchanged() -> None:
    data: list[int] = []
    method = data.append

    assert make_immutable(method) is method


def test_make_immutable_returns_builtin_function_unchanged() -> None:
    assert make_immutable(len) is len


def test_make_immutable_returns_frozenset_unchanged() -> None:
    values = frozenset({1, 2, 3})

    assert make_immutable(values) is values


def test_make_immutable_returns_immutable_list_unchanged() -> None:
    immutable = ImmutableList([1, 2, 3], make_immutable)

    assert make_immutable(immutable) is immutable


def test_make_immutable_returns_immutable_dict_unchanged() -> None:
    immutable = ImmutableDict({"a": 1}, make_immutable)

    assert make_immutable(immutable) is immutable


def test_make_immutable_returns_immutable_set_unchanged() -> None:
    immutable = ImmutableSet({"a", "b"}, make_immutable)

    assert make_immutable(immutable) is immutable


def test_make_immutable_converts_list_and_blocks_mutations() -> None:
    value = make_immutable([1, 2, 3])

    assert isinstance(value, ImmutableList)
    assert value == [1, 2, 3]

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable list"):
        value.append(4)


def test_make_immutable_converts_dict_and_blocks_mutations() -> None:
    value = make_immutable({"a": 1})

    assert isinstance(value, ImmutableDict)
    assert value == {"a": 1}

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable dict"):
        value["b"] = 2


def test_make_immutable_converts_set_and_blocks_mutations() -> None:
    value = make_immutable({1, 2, 3})

    assert isinstance(value, ImmutableSet)
    assert value == {1, 2, 3}

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable set"):
        value.add(4)


def test_immutable_list_from_list_creates_copy() -> None:
    original = [1, 2, 3]
    immutable = ImmutableList(original, make_immutable)
    original.append(4)

    assert immutable == [1, 2, 3]


def test_immutable_dict_from_dict_creates_copy() -> None:
    original = {"a": 1}
    immutable = ImmutableDict(original, make_immutable)
    original["b"] = 2

    assert immutable == {"a": 1}


def test_immutable_set_from_set_creates_copy() -> None:
    original = {1, 2}
    immutable = ImmutableSet(original, make_immutable)
    original.add(3)

    assert immutable == {1, 2}


class Address:
    def __init__(self, city: str) -> None:
        self.city = city


class User:
    def __init__(self) -> None:
        self.name = "Alf"
        self.age = 30
        self.tags = ["dev"]
        self.meta = {"active": True}
        self.groups = {"backend"}
        self.address = Address("Madrid")

    def describe(self) -> str:
        return f"{self.name}-{self.age}"

    def increase_age(self) -> None:
        self.age += 1


def test_make_immutable_custom_object_copies_public_state() -> None:
    user = User()

    immutable = make_immutable(user)

    assert immutable is not user
    assert type(immutable).__name__ == "ImmutableUser"
    assert immutable.name == "Alf"
    assert immutable.age == 30


def test_make_immutable_custom_object_blocks_setattr() -> None:
    immutable = make_immutable(User())

    with pytest.raises(
        MutationForbiddenException,
        match="Cannot modify an immutable object User",
    ):
        immutable.name = "Otro"


def test_make_immutable_custom_object_blocks_delattr() -> None:
    immutable = make_immutable(User())

    with pytest.raises(
        MutationForbiddenException,
        match="Cannot modify an immutable object User",
    ):
        del immutable.name


def test_make_immutable_custom_object_wraps_nested_containers_on_read() -> None:
    immutable = make_immutable(User())

    assert isinstance(immutable.tags, ImmutableList)
    assert isinstance(immutable.meta, ImmutableDict)
    assert isinstance(immutable.groups, ImmutableSet)

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable list"):
        immutable.tags.append("x")


def test_make_immutable_custom_object_wraps_nested_custom_objects_on_read() -> None:
    immutable = make_immutable(User())

    address = immutable.address
    assert type(address).__name__ == "ImmutableAddress"

    with pytest.raises(
        MutationForbiddenException,
        match="Cannot modify an immutable object",
    ):
        address.city = "Barcelona"


def test_make_immutable_custom_object_keeps_methods_callable() -> None:
    immutable = make_immutable(User())

    assert immutable.describe() == "Alf-30"


def test_make_immutable_custom_object_blocks_mutating_method_body() -> None:
    immutable = make_immutable(User())

    with pytest.raises(
        MutationForbiddenException,
        match="Cannot modify an immutable object",
    ):
        immutable.increase_age()


def test_make_immutable_custom_object_generated_class_is_cached_per_type() -> None:
    _immutable_cache.clear()

    first = make_immutable(User())
    second = make_immutable(User())

    assert type(first) is type(second)


def test_make_immutable_custom_object_with_slots_is_copied() -> None:
    class SlotUser:
        __slots__ = ("name", "tags")

        def __init__(self) -> None:
            self.name = "Slot"
            self.tags = ["a"]

    immutable = make_immutable(SlotUser())

    assert immutable.name == "Slot"
    assert isinstance(immutable.tags, ImmutableList)


def test_make_immutable_custom_object_with_unassigned_slot_does_not_crash() -> None:
    class SlotMaybe:
        __slots__ = ("x", "y")

        def __init__(self) -> None:
            self.x = 1
            # y no se asigna

    immutable = make_immutable(SlotMaybe())

    assert immutable.x == 1
    with pytest.raises(AttributeError):
        _ = immutable.y


def test_make_immutable_custom_object_dunder_getattribute_still_works() -> None:
    immutable = make_immutable(User())

    assert immutable.__class__.__name__.startswith("Immutable")


def test_copy_of_immutable_container_raises_due_to_mutation_protection() -> None:
    immutable_list = ImmutableList([1, 2], make_immutable)

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable list"):
        copy(immutable_list)


def test_make_immutable_does_not_modify_original_custom_instance() -> None:
    user = User()
    immutable = make_immutable(user)

    assert user.name == "Alf"
    assert immutable.name == "Alf"

    with pytest.raises(
        MutationForbiddenException,
        match="Cannot modify an immutable object",
    ):
        immutable.name = "cambio"

    assert user.name == "Alf"


def test_make_immutable_nested_read_returns_immutable_each_time() -> None:
    immutable = make_immutable(User())

    first = immutable.address
    second = immutable.address

    assert type(first) is type(second)
    assert first is not second
    with pytest.raises(
        MutationForbiddenException,
        match="Cannot modify an immutable object",
    ):
        first.city = "X"


def test_make_immutable_keeps_boolean_identity() -> None:
    assert make_immutable(True) is True
    assert make_immutable(False) is False


def test_make_immutable_keeps_datetime_objects_unchanged() -> None:
    value = datetime.datetime(2026, 5, 17, 18, 44, 30, 547255, tzinfo=datetime.timezone.utc)

    assert make_immutable(value) is value


def test_make_immutable_custom_object_nested_bound_method_is_callable() -> None:
    immutable = make_immutable(User())
    append = immutable.tags.count

    assert callable(append)
    assert append("dev") == 1


def test_make_immutable_keeps_decimal_unchanged() -> None:
    value = decimal.Decimal("123.45")

    assert make_immutable(value) is value


def test_make_immutable_keeps_uuid_unchanged() -> None:
    value = uuid.UUID("12345678-1234-5678-1234-567812345678")

    assert make_immutable(value) is value


def test_immutable_list_getters_return_immutable_values() -> None:
    immutable = make_immutable([[1], {"a": []}, {Address("Madrid")}])

    first = immutable[0]
    sliced = immutable[:2]
    iterated = list(immutable)

    assert isinstance(first, ImmutableList)
    assert isinstance(sliced, ImmutableList)
    assert isinstance(iterated[1], ImmutableDict)
    assert type(next(iter(iterated[2]))).__name__ == "ImmutableAddress"

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable list"):
        first.append(2)


def test_immutable_dict_getters_return_immutable_values() -> None:
    immutable = make_immutable({"items": [], "meta": {"nested": []}})

    item = immutable["items"]
    item_from_get = immutable.get("items")
    values = list(immutable.values())
    pairs = dict(immutable.items())

    assert isinstance(item, ImmutableList)
    assert isinstance(item_from_get, ImmutableList)
    assert isinstance(values[0], ImmutableList)
    assert isinstance(pairs["meta"], ImmutableDict)

    with pytest.raises(MutationForbiddenException, match="Cannot modify an immutable list"):
        item_from_get.append(1)


def test_immutable_set_getters_return_immutable_values() -> None:
    address = Address("Madrid")
    immutable = make_immutable({address})

    item = next(iter(immutable))

    assert type(item).__name__ == "ImmutableAddress"

    with pytest.raises(
        MutationForbiddenException,
        match="Cannot modify an immutable object Address",
    ):
        item.city = "Barcelona"


def test_get_wrapped_methods_returns_supported_dunders_defined_by_object() -> None:
    class Comparable:
        def __gt__(self, other) -> bool:
            return True

    methods = get_wrapped_methods(Comparable)

    assert "__gt__" in methods


def test_make_immutable_custom_object_wraps_comparison_dunder() -> None:
    class Comparable:
        def __init__(self, value: int) -> None:
            self.value = value

        def __gt__(self, other) -> bool:
            return self.value > other.value

    immutable = make_immutable(Comparable(2))

    assert immutable > Comparable(1)


def test_make_immutable_custom_object_blocks_setitem_dunder() -> None:
    class ItemContainer:
        def __init__(self) -> None:
            self.values: dict = {}

        def __setitem__(self, key, value) -> None:
            self.values[key] = value

    immutable = make_immutable(ItemContainer())

    with pytest.raises(
        MutationForbiddenException,
        match="Cannot modify an immutable object ItemContainer",
    ):
        immutable["key"] = "value"


def test_make_immutable_custom_object_blocks_inplace_dunder() -> None:
    class Addable:
        def __init__(self, value: int) -> None:
            self.value = value

        def __iadd__(self, value: int):
            self.value += value
            return self

    immutable = make_immutable(Addable(1))

    with pytest.raises(
        MutationForbiddenException,
        match="Cannot modify an immutable object Addable",
    ):
        immutable += 1
