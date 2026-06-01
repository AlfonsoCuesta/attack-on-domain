from __future__ import annotations

import inspect
from dataclasses import dataclass, field

from aod._internal.core.type_checking.extractors import extract_types_from_annotation

from aod._internal.core.type_utils import type_name


@dataclass
class MethodDoc:
    name: str
    signature: str
    doc: str


@dataclass
class FieldDoc:
    name: str
    type_name: str
    types: list[type] = field(default_factory=list)


@dataclass
class TypeDoc:
    name: str
    stereotype: str
    doc: str
    fields: list[FieldDoc] = field(default_factory=list)
    methods: list[MethodDoc] = field(default_factory=list)


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
        types = [t for t in extract_types_from_annotation(annotation) if isinstance(t, type)]
        result.append(FieldDoc(name=name, type_name=type_name(annotation), types=types))
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
