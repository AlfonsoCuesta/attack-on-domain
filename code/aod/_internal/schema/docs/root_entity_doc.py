from __future__ import annotations

import inspect
from dataclasses import dataclass, field

from aod._internal.application.contracts import Command, Query
from aod._internal.domain.entity import RootEntity
from aod._internal.schema.describe_utils import extract_fields, extract_methods
from aod._internal.schema.docs.generic_docs import FieldDoc, MethodDoc

type ContractType = type[Command] | type[Query]


@dataclass
class RootEntityDoc:
    name: str
    description: str = ""
    fields: list[FieldDoc] = field(default_factory=list)
    methods: list[MethodDoc] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)

    @classmethod
    def from_root_entity(
        cls,
        root_cls: type[RootEntity],
        contracts: list[ContractType] | None = None,
    ) -> RootEntityDoc:
        commands: list[str] = []
        queries: list[str] = []
        for c in contracts or []:
            if issubclass(c, Command):
                commands.append(c.__name__)
            elif issubclass(c, Query):
                queries.append(c.__name__)
        return cls(
            name=root_cls.__name__,
            description=inspect.getdoc(root_cls) or "",
            fields=extract_fields(root_cls),
            methods=extract_methods(root_cls),
            commands=commands,
            queries=queries,
        )
