from __future__ import annotations

import typing
from types import UnionType


def unwrap_union(annotation: object) -> tuple[object, ...]:
    origin = typing.get_origin(annotation)
    if origin is UnionType or origin is typing.Union:
        return tuple(a for a in typing.get_args(annotation) if a is not type(None))
    return (annotation,)


def type_name(annotation: object) -> str:
    origin = typing.get_origin(annotation)
    if origin is not None:
        args = typing.get_args(annotation)
        filtered = [a for a in args if a is not type(None)]
        if origin is typing.Union and len(filtered) == 1:
            return type_name(filtered[0])
        items = ", ".join(type_name(a) for a in filtered)
        origin_name = getattr(origin, "__name__", str(origin))
        return f"{origin_name}[{items}]"
    if isinstance(annotation, type):
        return annotation.__name__
    return str(annotation)
