from __future__ import annotations

import inspect
from collections.abc import Callable

from aod._internal.schema.docs.generic_docs import (
    FieldDoc,
    MethodDoc,
    ParamDoc,
    type_str,
    default_str,
)


def extract_params(func: Callable[..., object]) -> list[ParamDoc]:
    try:
        sig = inspect.signature(func)
    except ValueError, TypeError:
        return []
    params: list[ParamDoc] = []
    for pname, p in sig.parameters.items():
        if pname == "self":
            continue
        params.append(
            ParamDoc(name=pname, type_name=type_str(p.annotation), default=default_str(p.default))
        )
    return params


def extract_fields(cls: type) -> list[FieldDoc]:
    fields = getattr(cls, "__model_fields__", None)
    if fields is None:
        return []
    result: list[FieldDoc] = []
    for name, info in fields.items():
        if name.startswith("_"):
            continue
        result.append(FieldDoc.from_field(name, info))
    return result


def extract_methods(cls: type) -> list[MethodDoc]:
    result: list[MethodDoc] = []
    for name, val in cls.__dict__.items():
        if name.startswith("_"):
            continue
        if not inspect.isfunction(val):
            continue
        result.append(MethodDoc.from_method(val))
    return result
