from __future__ import annotations

from dataclasses import dataclass

from aod._internal.schema.docs.bounded_context_doc import BoundedContextDoc
from aod._internal.schema.docs.infrastructure_doc import InfrastructureDoc
from aod._internal.schema.module import Module


@dataclass
class ModuleDoc:
    name: str
    domain: BoundedContextDoc
    infrastructure: InfrastructureDoc

    @classmethod
    def from_module(cls, mod: Module) -> ModuleDoc:
        return cls(
            name=mod.name,
            domain=BoundedContextDoc.from_bounded_context(mod.context),
            infrastructure=InfrastructureDoc.from_infrastructure(mod.infrastructure),
        )
