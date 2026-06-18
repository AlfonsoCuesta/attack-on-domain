from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined


def type_str(tp: object) -> str:
    if tp is inspect.Parameter.empty or tp is inspect.Signature.empty:
        return ""
    if isinstance(tp, type):
        return tp.__name__
    origin = getattr(tp, "__origin__", None)
    if origin is not None:
        args = getattr(tp, "__args__", ())
        args_str = ", ".join(type_str(a) for a in args)
        return f"{type_str(origin)}[{args_str}]"
    return str(tp)


def default_str(default: object) -> str:
    if default is PydanticUndefined or default is inspect.Parameter.empty:
        return ""
    if default is None:
        return "None"
    return repr(default)


@dataclass
class FieldDoc:
    name: str
    type_name: str = ""
    default: str = ""
    description: str = ""

    @classmethod
    def from_field(cls, name: str, info: FieldInfo) -> FieldDoc:
        annotation = info.annotation
        if annotation is None:
            return cls(name=name)
        return cls(
            name=name,
            type_name=type_str(annotation),
            default=default_str(info.default),
            description=info.description or "",
        )


@dataclass
class ParamDoc:
    name: str
    type_name: str = ""
    default: str = ""
    description: str = ""


@dataclass
class MethodDoc:
    name: str
    params: list[ParamDoc] = field(default_factory=list)
    return_type: str = ""
    description: str = ""

    @classmethod
    def from_method(cls, func: Any) -> MethodDoc:
        func_name = getattr(func, "__name__", "")
        try:
            sig = inspect.signature(func)
        except ValueError, TypeError:
            return cls(name=func_name)
        params: list[ParamDoc] = []
        for pname, p in sig.parameters.items():
            if pname in ("self", "cls"):
                continue
            params.append(
                ParamDoc(
                    name=pname,
                    type_name=type_str(p.annotation),
                    default=default_str(p.default),
                )
            )
        return_type = (
            type_str(sig.return_annotation)
            if sig.return_annotation is not inspect.Signature.empty
            else ""
        )
        description = inspect.getdoc(func) or ""
        return cls(name=func_name, params=params, return_type=return_type, description=description)
