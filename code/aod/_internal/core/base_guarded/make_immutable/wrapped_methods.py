from collections.abc import Callable
from typing import Any

from ...domain_exception import MutationForbiddenException

_SKIP_DUNDERS = frozenset(
    {
        "__init__",
        "__new__",
        "__class__",
        "__dict__",
        "__module__",
        "__doc__",
        "__annotations__",
        "__init_subclass__",
        "__subclasshook__",
    }
)

_MUTATING_DUNDERS = frozenset(
    {
        "__setattr__",
        "__setitem__",
        "__delattr__",
        "__delitem__",
        "__iadd__",
        "__iand__",
        "__ifloordiv__",
        "__ilshift__",
        "__imod__",
        "__imul__",
        "__ior__",
        "__ipow__",
        "__irshift__",
        "__isub__",
        "__itruediv__",
        "__ixor__",
        "__aenter__",
        "__aexit__",
    }
)

_READONLY_DUNDERS = frozenset(
    {
        "__eq__",
        "__ne__",
        "__lt__",
        "__le__",
        "__gt__",
        "__ge__",
        "__bool__",
        "__hash__",
        "__repr__",
        "__str__",
        "__bytes__",
        "__complex__",
        "__float__",
        "__format__",
        "__index__",
        "__int__",
        "__round__",
        "__trunc__",
        "__contains__",
        "__getitem__",
        "__iter__",
        "__len__",
        "__length_hint__",
        "__missing__",
        "__reversed__",
        "__abs__",
        "__ceil__",
        "__floor__",
        "__invert__",
        "__neg__",
        "__pos__",
        "__copy__",
        "__deepcopy__",
        "__add__",
        "__sub__",
        "__mul__",
        "__truediv__",
        "__floordiv__",
        "__mod__",
        "__divmod__",
        "__pow__",
        "__lshift__",
        "__rshift__",
        "__and__",
        "__xor__",
        "__or__",
        "__matmul__",
        "__radd__",
        "__rsub__",
        "__rmul__",
        "__rtruediv__",
        "__rfloordiv__",
        "__rmod__",
        "__rdivmod__",
        "__rpow__",
        "__rlshift__",
        "__rrshift__",
        "__rand__",
        "__rxor__",
        "__ror__",
        "__rmatmul__",
    }
)

_WRAP_RESULT_DUNDERS = frozenset(
    {
        "__getitem__",
        "__missing__",
        "__abs__",
        "__add__",
        "__and__",
        "__ceil__",
        "__divmod__",
        "__floor__",
        "__floordiv__",
        "__invert__",
        "__lshift__",
        "__matmul__",
        "__mod__",
        "__mul__",
        "__neg__",
        "__or__",
        "__pos__",
        "__pow__",
        "__round__",
        "__rshift__",
        "__sub__",
        "__truediv__",
        "__xor__",
        "__radd__",
        "__rsub__",
        "__rmul__",
        "__rtruediv__",
        "__rfloordiv__",
        "__rmod__",
        "__rdivmod__",
        "__rpow__",
        "__rlshift__",
        "__rrshift__",
        "__rand__",
        "__rxor__",
        "__ror__",
        "__rmatmul__",
    }
)


def _is_mutating_dunder(name: str) -> bool:
    return name in _MUTATING_DUNDERS


def _is_readonly_dunder(name: str) -> bool:
    return name in _READONLY_DUNDERS


def _should_wrap_result(name: str) -> bool:
    return name in _WRAP_RESULT_DUNDERS


def _unwrap(value: Any) -> Any:
    return getattr(value, "__wrapped_object__", value)


def _wrap_result(self: Any, value: Any) -> Any:
    factory = object.__getattribute__(self, "__immutable_factory__")
    return factory(value)


def _wrap_iterator(self: Any, iterator) -> Any:
    for value in iterator:
        yield _wrap_result(self, value)


def _make_wrapped_method(name: str) -> Callable:
    def _wrapped(self, *args, **kwargs):
        wrapped = object.__getattribute__(self, "__wrapped_object__")
        method = getattr(wrapped, name)
        unwrapped_args = tuple(_unwrap(arg) for arg in args)
        unwrapped_kwargs = {key: _unwrap(value) for key, value in kwargs.items()}
        result = method(*unwrapped_args, **unwrapped_kwargs)

        if name in ("__iter__", "__reversed__"):
            return _wrap_iterator(self, result)
        if _should_wrap_result(name):
            return _wrap_result(self, result)
        return result

    _wrapped.__name__ = name
    return _wrapped


def _make_blocked_method(name: str) -> Callable:
    def _blocked(self, *args, **kwargs):
        immutable_class = object.__getattribute__(self, "__immutable_class__")
        raise MutationForbiddenException(
            f"Cannot modify an immutable object {immutable_class.__name__}"
        )

    _blocked.__name__ = name
    return _blocked


def get_wrapped_methods(cls: type) -> dict[str, Callable]:
    wrapped = {}
    for klass in cls.__mro__:
        for name in getattr(klass, "__dict__", {}):
            if not name.startswith("__") or not name.endswith("__"):
                continue
            if name in _SKIP_DUNDERS:
                continue
            if _is_readonly_dunder(name):
                wrapped[name] = _make_wrapped_method(name)
            elif _is_mutating_dunder(name):
                wrapped[name] = _make_blocked_method(name)
    return wrapped
