from typing import Any

from .immutable_custom import _make_immutable_object
from .immutable_dict import ImmutableDict
from .immutable_list import ImmutableList
from .immutable_set import ImmutableSet


def _has_instance_state(obj: Any) -> bool:
    cls = type(obj)
    if cls.__new__ is not object.__new__:
        return False
    if hasattr(obj, "__dict__"):
        return True
    return bool(getattr(cls, "__slots__", ())) and cls.__module__ != "uuid"


def make_immutable(value: Any) -> Any:
    if isinstance(value, ImmutableList | ImmutableDict | ImmutableSet):
        return value
    if getattr(value, "__immutable_class__", None):
        return value
    if isinstance(value, list):
        return ImmutableList(value, make_immutable)
    if isinstance(value, dict):
        return ImmutableDict(value, make_immutable)
    if isinstance(value, set):
        return ImmutableSet(value, make_immutable)
    if isinstance(value, tuple):
        return tuple(make_immutable(item) for item in value)
    if isinstance(value, frozenset):
        return frozenset(make_immutable(item) for item in value)
    if not _has_instance_state(value):
        return value
    return _make_immutable_object(value, make_immutable)
