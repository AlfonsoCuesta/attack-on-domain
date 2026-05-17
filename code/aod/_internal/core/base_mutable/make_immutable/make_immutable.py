from types import BuiltinFunctionType, BuiltinMethodType, FunctionType, MethodType

from .immutable_custom import _make_immutable_object
from .immutable_dict import ImmutableDict
from .immutable_list import ImmutableList
from .immutable_set import ImmutableSet

_PRIMITIVE_TYPES = (int, float, str, bool, bytes, type(None))

_CALLABLE_TYPES = (MethodType, FunctionType, BuiltinMethodType, BuiltinFunctionType)


def make_immutable(value):
    if isinstance(value, _PRIMITIVE_TYPES):
        return value
    if isinstance(value, _CALLABLE_TYPES):
        return value
    if isinstance(value, ImmutableList | ImmutableDict | ImmutableSet | frozenset):
        return value
    if isinstance(value, list):
        return ImmutableList.from_list(value)
    if isinstance(value, dict):
        return ImmutableDict.from_dict(value)
    if isinstance(value, set):
        return ImmutableSet.from_set(value)
    return _make_immutable_object(value, make_immutable)
