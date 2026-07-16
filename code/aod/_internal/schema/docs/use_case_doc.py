from __future__ import annotations

import inspect
from dataclasses import dataclass, field

from aod._internal.application.port import Port
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.schema.describe_utils import extract_params
from aod._internal.schema.docs.handler_port_doc import HandlerPortDoc
from aod._internal.schema.docs.generic_docs import ParamDoc
from aod._internal.schema.docs.port_doc import PortDoc


@dataclass
class UseCaseDoc:
    name: str
    description: str = ""
    is_async: bool = False
    ports: list[PortDoc] = field(default_factory=list)
    handler_ports: list[HandlerPortDoc] = field(default_factory=list)
    params: list[ParamDoc] = field(default_factory=list)

    @classmethod
    def from_use_case(cls, uc_cls: type[UseCase] | type[AsyncUseCase]) -> UseCaseDoc:
        ports: list[PortDoc] = []
        handler_ports: list[HandlerPortDoc] = []
        is_async = issubclass(uc_cls, AsyncUseCase)

        uc_fields = getattr(uc_cls, "__model_fields__", None)
        if uc_fields is not None:
            for fname, finfo in uc_fields.items():
                annotation = finfo.annotation

                hp = HandlerPortDoc.from_handler_port(fname, annotation)
                if hp is not None:
                    handler_ports.append(hp)
                elif (
                    isinstance(annotation, type)
                    and issubclass(annotation, Port)
                    and annotation is not Port
                ):
                    ports.append(PortDoc.from_port(annotation))

        return cls(
            name=uc_cls.__name__,
            description=inspect.getdoc(uc_cls) or "",
            is_async=is_async,
            ports=ports,
            handler_ports=handler_ports,
            params=extract_params(uc_cls.run),
        )
