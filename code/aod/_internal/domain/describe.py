from __future__ import annotations

import inspect
import typing
from dataclasses import dataclass, field


@dataclass
class MethodDoc:
    name: str
    signature: str
    doc: str


@dataclass
class FieldDoc:
    name: str
    type_name: str


@dataclass
class TypeDoc:
    name: str
    stereotype: str
    doc: str
    fields: list[FieldDoc] = field(default_factory=list)
    methods: list[MethodDoc] = field(default_factory=list)


def _type_name(tp: type) -> str:
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin is not None:
        if args:
            args_str = ", ".join(_type_name(a) for a in args)
            return f"{_type_name(origin)}[{args_str}]"
        return _type_name(origin)
    return getattr(tp, "__name__", str(tp))


def _extract_fields(cls: type) -> list[FieldDoc]:
    fields = getattr(cls, "__model_fields__", None)
    if fields is None:
        return []

    result = []
    for name, field_info in fields.items():
        if name.startswith("_"):
            continue
        annotation = field_info.annotation
        if annotation is None:
            continue
        result.append(FieldDoc(name=name, type_name=_type_name(annotation)))
    return result


def _extract_methods(cls: type) -> list[MethodDoc]:
    result = []
    for name in sorted(cls.__dict__):
        if name.startswith("_"):
            continue
        val = cls.__dict__[name]
        if not callable(val):
            continue
        try:
            sig = inspect.signature(val)
            sig_str = str(sig)
        except Exception:
            sig_str = "(...)"
        doc = inspect.getdoc(val) or ""
        result.append(MethodDoc(name=name, signature=sig_str, doc=doc))
    return result
