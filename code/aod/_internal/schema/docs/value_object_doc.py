from __future__ import annotations

from dataclasses import dataclass, field

from aod._internal.domain.value_object import ValueObject
from aod._internal.schema.describe_utils import extract_fields, extract_methods
from aod._internal.schema.docs.generic_docs import FieldDoc, MethodDoc


@dataclass
class ValueObjectDoc:
    name: str
    description: str = ""
    fields: list[FieldDoc] = field(default_factory=list)
    methods: list[MethodDoc] = field(default_factory=list)

    @classmethod
    def from_value_object(cls, vo_cls: type[ValueObject]) -> ValueObjectDoc:
        return cls(
            name=vo_cls.__name__,
            description=vo_cls.__doc__ or "",
            fields=extract_fields(vo_cls),
            methods=extract_methods(vo_cls),
        )
