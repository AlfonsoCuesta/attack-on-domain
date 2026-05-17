from typing import Any

from ...domain_exception import MutationForbiddenError

_immutable_cache: dict[type, type] = {}


def _make_immutable_class(cls: type, factory) -> type:
    def _raise_set(self, name, value):
        raise MutationForbiddenError(f"Cannot set '{name}' on an immutable object")

    def _raise_del(self, name):
        raise MutationForbiddenError(f"Cannot delete '{name}' on an immutable object")

    def _getattribute(self, name):
        value = super(immutable_cls, self).__getattribute__(name)
        return factory(value)  # factory inyectado, sin import circular

    immutable_cls = type(
        f"Immutable{cls.__name__}",
        (cls,),
        {
            "__setattr__": _raise_set,
            "__delattr__": _raise_del,
            "__getattribute__": _getattribute,
        },
    )
    return immutable_cls


def _copy_state(src: Any, dst: Any) -> None:
    if hasattr(src, "__dict__"):
        dst.__dict__.update(src.__dict__)

    for klass in type(src).__mro__:
        for slot in getattr(klass, "__slots__", ()):
            if slot == "__dict__":
                continue
            try:
                object.__setattr__(dst, slot, getattr(src, slot))
            except AttributeError:
                pass  # slot declarado pero no asignado


def _make_immutable_object(obj, factory) -> object:
    cls = type(obj)
    if cls not in _immutable_cache:
        _immutable_cache[cls] = _make_immutable_class(cls, factory)

    immutable_cls = _immutable_cache[cls]
    new_obj = object.__new__(immutable_cls)
    _copy_state(obj, new_obj)
    return new_obj
