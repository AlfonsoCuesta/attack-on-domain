from code.aod._internal.core.domain_exception import MutationForbiddenError
from copy import copy
from functools import wraps
from typing import Any

PRIMITIVE_TYPES = (int, float, str, bool, bytes, type(None))


def create_mutable_proxy(obj):
    if type(obj) in PRIMITIVE_TYPES:
        return obj


class MutableObjectProxy:
    def __init__(self, wrapped: Any):
        self._wrapped = wrapped

    def __getattribute__(self, name):
        wrapped = object.__getattribute__(self, "_wrapped")
        attr = getattr(wrapped, name)
        if type(attr) in PRIMITIVE_TYPES:
            return attr

        if callable(attr):

            @wraps(attr)
            def guarded(*args, **kwargs):
                snapshot = copy(wrapped)
                result = attr(*args, **kwargs)
                if wrapped != snapshot:
                    raise MutationForbiddenError()
                return result

            return guarded

        return MutableObjectProxy(attr)

    def __eq__(self, other):
        return object.__getattribute__(self, "_wrapped") == other

    def __repr__(self):
        return repr(object.__getattribute__(self, "_wrapped"))
