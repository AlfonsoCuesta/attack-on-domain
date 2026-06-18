from __future__ import annotations

from dataclasses import dataclass, field

from aod._internal.application.contracts import Command, Query
from aod._internal.schema.describe_utils import extract_fields, extract_methods
from aod._internal.schema.docs.generic_docs import FieldDoc, MethodDoc


@dataclass
class ContractDoc:
    name: str
    kind: str = ""
    fields: list[FieldDoc] = field(default_factory=list)
    methods: list[MethodDoc] = field(default_factory=list)

    @classmethod
    def from_contract(cls, contract_cls: type[Command] | type[Query]) -> ContractDoc:
        kind = "command" if issubclass(contract_cls, Command) else "query"
        return cls(
            name=contract_cls.__name__,
            kind=kind,
            fields=extract_fields(contract_cls),
            methods=extract_methods(contract_cls),
        )
