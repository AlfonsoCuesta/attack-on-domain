from collections.abc import Callable
from typing import Any

from ...domain_exception import MutationForbiddenException

_COMPARISON_METHODS = (
    "__eq__",
    "__ne__",
    "__lt__",
    "__le__",
    "__gt__",
    "__ge__",
)

_CONVERSION_METHODS = (
    "__bool__",
    "__bytes__",
    "__complex__",
    "__float__",
    "__format__",
    "__hash__",
    "__index__",
    "__int__",
    "__repr__",
    "__round__",
    "__str__",
    "__trunc__",
)

_CONTAINER_METHODS = (
    "__contains__",
    "__getitem__",
    "__iter__",
    "__len__",
    "__length_hint__",
    "__missing__",
    "__reversed__",
)

_UNARY_NUMERIC_METHODS = (
    "__abs__",
    "__ceil__",
    "__floor__",
    "__invert__",
    "__neg__",
    "__pos__",
)

_BINARY_NUMERIC_METHODS = (
    "__add__",
    "__and__",
    "__divmod__",
    "__floordiv__",
    "__lshift__",
    "__matmul__",
    "__mod__",
    "__mul__",
    "__or__",
    "__pow__",
    "__radd__",
    "__rand__",
    "__rdivmod__",
    "__rfloordiv__",
    "__rlshift__",
    "__rmatmul__",
    "__rmod__",
    "__rmul__",
    "__ror__",
    "__round__",
    "__rpow__",
    "__rrshift__",
    "__rshift__",
    "__rsub__",
    "__rtruediv__",
    "__rxor__",
    "__sub__",
    "__truediv__",
    "__xor__",
)

_MUTATING_METHODS = (
    "__delitem__",
    "__delete__",
    "__iadd__",
    "__iand__",
    "__ifloordiv__",
    "__ilshift__",
    "__imatmul__",
    "__imod__",
    "__imul__",
    "__ior__",
    "__ipow__",
    "__irshift__",
    "__isub__",
    "__itruediv__",
    "__ixor__",
    "__set__",
    "__setitem__",
    "__setattr__",
    "__delattr__",
)

_WRAPPED_METHODS = (
    *_COMPARISON_METHODS,
    *_CONVERSION_METHODS,
    *_CONTAINER_METHODS,
    *_UNARY_NUMERIC_METHODS,
    *_BINARY_NUMERIC_METHODS,
)

_FACTORY_RESULT_METHODS = (
    "__getitem__",
    "__missing__",
    *_UNARY_NUMERIC_METHODS,
    *_BINARY_NUMERIC_METHODS,
)


def _unwrap(value: Any) -> Any:
    return getattr(value, "__wrapped_object__", value)


def _wrap_result(self: Any, value: Any) -> Any:
    factory = object.__getattribute__(self, "__immutable_factory__")
    return factory(value)


def _wrap_iterator(self: Any, iterator) -> Any:
    for value in iterator:
        yield _wrap_result(self, value)


def _has_dunder(cls: type, name: str) -> bool:
    return any(name in klass.__dict__ for klass in cls.__mro__)


def _make_wrapped_method(name: str) -> Callable:
    def _wrapped(self, *args, **kwargs):
        wrapped = object.__getattribute__(self, "__wrapped_object__")
        method = getattr(wrapped, name)
        unwrapped_args = tuple(_unwrap(arg) for arg in args)
        unwrapped_kwargs = {key: _unwrap(value) for key, value in kwargs.items()}
        result = method(*unwrapped_args, **unwrapped_kwargs)

        if name in ("__iter__", "__reversed__"):
            return _wrap_iterator(self, result)
        if name in _FACTORY_RESULT_METHODS:
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
    wrapped_methods = {
        name: _make_wrapped_method(name)
        for name in _WRAPPED_METHODS
        if _has_dunder(cls, name)
    }
    blocked_methods = {
        name: _make_blocked_method(name)
        for name in _MUTATING_METHODS
        if _has_dunder(cls, name)
    }
    return {**wrapped_methods, **blocked_methods}
