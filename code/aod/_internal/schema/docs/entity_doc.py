from __future__ import annotations

import inspect
from dataclasses import dataclass, field

from aod._internal.domain.entity import Entity
from aod._internal.schema.describe_utils import extract_fields, extract_methods
from aod._internal.schema.docs.generic_docs import FieldDoc, MethodDoc


@dataclass
class EntityDoc:
    name: str
    description: str = ""
    fields: list[FieldDoc] = field(default_factory=list)
    methods: list[MethodDoc] = field(default_factory=list)

    @classmethod
    def from_entity(cls, ent_cls: type[Entity]) -> EntityDoc:
        return cls(
            name=ent_cls.__name__,
            description=inspect.getdoc(ent_cls) or "",
            fields=extract_fields(ent_cls),
            methods=extract_methods(ent_cls),
        )
