from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field

from aod._internal.core.fields import is_public_field
from aod._internal.core.type_checking.extractors import extract_types_from_annotation
from aod._internal.core.type_utils import type_name

__all__ = [
    "FieldDoc",
    "MethodDoc",
    "ParamDoc",
    "TypeDoc",
    "describe",
    "extract_fields",
    "extract_methods",
]


@dataclass
class ParamDoc:
    name: str
    type_name: str


@dataclass
class MethodDoc:
    name: str
    signature: str
    doc: str
    params: list[ParamDoc] = field(default_factory=list)
    returns: str = ""


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


def _extract_params_and_return(val: Callable[..., object]) -> tuple[list[ParamDoc], str]:
    sig = inspect.signature(val)
    params: list[ParamDoc] = []
    for pname, p in sig.parameters.items():
        if pname in ("self", "cls"):
            continue
        ptype = type_name(p.annotation) if p.annotation is not inspect.Parameter.empty else ""
        params.append(ParamDoc(name=pname, type_name=ptype))
    returns = (
        type_name(sig.return_annotation)
        if sig.return_annotation is not inspect.Signature.empty
        else ""
    )
    return params, returns


def extract_fields(cls: type) -> list[FieldDoc]:
    fields = getattr(cls, "__model_fields__", None)
    if fields is None:
        return []

    result = []
    for name, field_info in fields.items():
        if not is_public_field(name):
            continue
        annotation = field_info.annotation
        if annotation is None:
            continue
        types = [t for t in extract_types_from_annotation(annotation) if isinstance(t, type)]
        result.append(FieldDoc(name=name, type_name=type_name(annotation), types=types))
    return result


def extract_methods(cls: type) -> list[MethodDoc]:
    result = []
    for name in sorted(cls.__dict__):
        if not is_public_field(name):
            continue
        val = cls.__dict__[name]
        if not callable(val):
            continue
        # fmt: off
        try:
            sig_str = str(inspect.signature(val))
            params, returns = _extract_params_and_return(val)
        except (ValueError, TypeError):
            sig_str = "(...)"
            params = []
            returns = ""
        # fmt: on
        doc = inspect.getdoc(val) or ""
        result.append(
            MethodDoc(name=name, signature=sig_str, doc=doc, params=params, returns=returns)
        )
    return result


def describe(cls: type, stereotype: str) -> TypeDoc:
    return TypeDoc(
        name=cls.__name__,
        stereotype=stereotype,
        doc=inspect.getdoc(cls) or "",
        fields=extract_fields(cls),
        methods=extract_methods(cls),
    )
