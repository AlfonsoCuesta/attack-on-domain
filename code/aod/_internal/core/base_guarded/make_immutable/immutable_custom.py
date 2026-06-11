import types
from typing import Any, Type

from .wrapped_methods import get_wrapped_methods

_immutable_cache: dict[type, type] = {}


def _copy_state(src: object, dst: object) -> None:
    if hasattr(src, "__dict__"):
        src_dict = object.__getattribute__(src, "__dict__")
        dst_dict = object.__getattribute__(dst, "__dict__")
        dst_dict.update(src_dict)

    for klass in type(src).__mro__:
        for slot in getattr(klass, "__slots__", ()):
            try:
                object.__setattr__(dst, slot, object.__getattribute__(src, slot))
            except AttributeError:
                pass


def _make_immutable_class(cls: Type, factory: Any) -> type:
    model_fields = getattr(cls, "__model_fields__", None)

    def __getattribute__(self: Any, name: str) -> Any:
        if name.startswith("__") and name.endswith("__"):
            return object.__getattribute__(self, name)
        value = object.__getattribute__(self, name)
        if isinstance(value, types.MethodType):
            return value
        if model_fields is not None and name not in model_fields:
            return value
        return factory(value)

    immutable_cls = type(
        f"Immutable{cls.__name__}",
        (cls,),
        {
            "__immutable_factory__": staticmethod(factory),
            "__immutable_class__": cls,
            "__wrapped_object__": None,
            "__getattribute__": __getattribute__,
            **get_wrapped_methods(cls),
        },
    )
    return immutable_cls


def _make_immutable_object(obj: Any, factory: Any) -> Any:
    cls = type(obj)
    if cls not in _immutable_cache:
        _immutable_cache[cls] = _make_immutable_class(cls, factory)

    immutable_cls = _immutable_cache[cls]
    try:
        new_obj: Any = immutable_cls.__new__(immutable_cls, obj)
    except TypeError:
        try:
            new_obj = object.__new__(immutable_cls)
        except TypeError:
            return obj

    _copy_state(obj, new_obj)
    object.__setattr__(new_obj, "__wrapped_object__", obj)
    return new_obj
