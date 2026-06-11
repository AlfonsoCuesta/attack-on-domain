import datetime
import decimal
import uuid
from types import BuiltinFunctionType, BuiltinMethodType, FunctionType, MethodType
from typing import Any

from .immutable_custom import _make_immutable_object
from .immutable_dict import ImmutableDict
from .immutable_list import ImmutableList
from .immutable_set import ImmutableSet

_PRIMITIVE_TYPES = (
    int,
    float,
    complex,
    str,
    bool,
    bytes,
    range,
    type(None),
    datetime.date,
    datetime.time,
    datetime.datetime,
    datetime.timedelta,
    datetime.timezone,
    decimal.Decimal,
    uuid.UUID,
)

_CALLABLE_TYPES = (MethodType, FunctionType, BuiltinMethodType, BuiltinFunctionType)


def make_immutable(value: Any) -> Any:
    if isinstance(value, _PRIMITIVE_TYPES):
        return value
    if isinstance(value, _CALLABLE_TYPES):
        return value
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
    return _make_immutable_object(value, make_immutable)
