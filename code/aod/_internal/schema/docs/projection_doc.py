from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import get_type_hints

from aod._internal.infrastructure.projection import ProjectionBase
from aod._internal.infrastructure.projection.projection import (
    AsyncProjection,
    AsyncReadProjection,
    AsyncWriteProjection,
    Projection,
    ReadProjection,
    WriteProjection,
)
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.schema.docs.generic_docs import MethodDoc
from aod._internal.schema.docs.port_doc import PortDoc

_PROJECTION_TYPES: dict[type, str] = {
    AsyncProjection: "AsyncProjection",
    AsyncWriteProjection: "AsyncWriteProjection",
    AsyncReadProjection: "AsyncReadProjection",
    Projection: "Projection",
    WriteProjection: "WriteProjection",
    ReadProjection: "ReadProjection",
}


@dataclass
class ProjectionDoc:
    name: str
    projection_type: str = ""
    session: str = ""
    ports: list[PortDoc] = field(default_factory=list)
    read: MethodDoc | None = None
    write: MethodDoc | None = None
    is_async: bool = False
    description: str = ""

    @classmethod
    def from_projection(cls, proj_cls: type[ProjectionBase]) -> ProjectionDoc:
        projection_type = _resolve_projection_type(proj_cls)
        is_async = projection_type.startswith("Async")

        hints = get_type_hints(proj_cls)
        session = _session_name(hints.get("session"))

        ports: list[PortDoc] = []
        fields = getattr(proj_cls, "__model_fields__", None)
        if fields is not None:
            for fname, finfo in fields.items():
                if fname == "session":
                    continue
                annotation = finfo.annotation
                from aod._internal.application.port import Port

                if (
                    isinstance(annotation, type)
                    and issubclass(annotation, Port)
                    and annotation is not Port
                ):
                    ports.append(PortDoc.from_port(annotation))

        read = None
        read_func = proj_cls.__dict__.get("read")
        if read_func is not None:
            read = MethodDoc.from_method(read_func)

        write = None
        write_func = proj_cls.__dict__.get("write")
        if write_func is not None:
            write = MethodDoc.from_method(write_func)

        return cls(
            name=proj_cls.__name__,
            projection_type=projection_type,
            session=session,
            ports=ports,
            read=read,
            write=write,
            is_async=is_async,
            description=inspect.getdoc(proj_cls) or "",
        )


def _resolve_projection_type(cls: type) -> str:
    for base, label in _PROJECTION_TYPES.items():
        if issubclass(cls, base):
            return label
    return ""


def _session_name(tp: object) -> str:
    if tp is None:
        return ""
    origin = getattr(tp, "__origin__", None)
    if origin is not None:
        args = getattr(tp, "__args__", ())
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, (Session, AsyncSession)):
                return arg.__name__
        return ""
    if isinstance(tp, type):
        return tp.__name__
    return str(tp)
