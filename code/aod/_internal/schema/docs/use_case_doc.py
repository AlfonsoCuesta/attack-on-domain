from __future__ import annotations

import inspect
from dataclasses import dataclass, field

from aod._internal.application.handler import CommandPort, QueryPort
from aod._internal.application.port import Port
from aod._internal.application.use_case import UseCase
from aod._internal.schema.describe_utils import extract_params
from aod._internal.schema.docs.generic_docs import ParamDoc
from aod._internal.schema.docs.port_doc import PortDoc


@dataclass
class UseCaseDoc:
    name: str
    description: str = ""
    ports: list[PortDoc] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    params: list[ParamDoc] = field(default_factory=list)

    @classmethod
    def from_use_case(cls, uc_cls: type[UseCase]) -> UseCaseDoc:
        ports: list[PortDoc] = []
        commands: list[str] = []
        queries: list[str] = []

        uc_fields = getattr(uc_cls, "__model_fields__", None)
        if uc_fields is not None:
            for fname, finfo in uc_fields.items():
                if fname.startswith("_"):
                    continue
                annotation = finfo.annotation
                if annotation is None:
                    continue

                origin = getattr(annotation, "__origin__", None)
                if origin is not None and issubclass(origin, (CommandPort, QueryPort)):
                    args = getattr(annotation, "__args__", ())
                    contract = args[0] if args else None
                    if contract is not None:
                        name = contract.__name__
                        if issubclass(origin, CommandPort):
                            commands.append(name)
                        else:
                            queries.append(name)
                elif (
                    isinstance(annotation, type)
                    and issubclass(annotation, Port)
                    and annotation is not Port
                ):
                    ports.append(PortDoc.from_port(annotation))

        return cls(
            name=uc_cls.__name__,
            description=inspect.getdoc(uc_cls) or "",
            ports=ports,
            commands=commands,
            queries=queries,
            params=extract_params(uc_cls.run),
        )
