from __future__ import annotations

import inspect
from dataclasses import dataclass, field

from aod._internal.application.port import Port
from aod._internal.schema.describe_utils import extract_fields, extract_methods
from aod._internal.schema.docs.generic_docs import FieldDoc, MethodDoc


@dataclass
class PortDoc:
    name: str
    type_name: str
    description: str = ""
    fields: list[FieldDoc] = field(default_factory=list)
    methods: list[MethodDoc] = field(default_factory=list)

    @classmethod
    def from_port(cls, port_cls: type[Port]) -> PortDoc:
        return cls(
            name=port_cls.__name__,
            type_name=port_cls.__name__,
            description=inspect.getdoc(port_cls) or "",
            fields=extract_fields(port_cls),
            methods=extract_methods(port_cls),
        )
