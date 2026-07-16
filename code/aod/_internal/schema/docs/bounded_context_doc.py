from __future__ import annotations

from dataclasses import dataclass, field

from aod._internal.schema.bounded_context import BoundedContext
from aod._internal.schema.docs.entity_doc import EntityDoc
from aod._internal.schema.docs.root_entity_doc import RootEntityDoc
from aod._internal.schema.docs.service_doc import ServiceDoc
from aod._internal.schema.docs.use_case_doc import UseCaseDoc
from aod._internal.schema.docs.value_object_doc import ValueObjectDoc


@dataclass
class BoundedContextDoc:
    name: str | None = None
    roots: list[RootEntityDoc] = field(default_factory=list)
    entities: list[EntityDoc] = field(default_factory=list)
    value_objects: list[ValueObjectDoc] = field(default_factory=list)
    services: list[ServiceDoc] = field(default_factory=list)
    use_cases: list[UseCaseDoc] = field(default_factory=list)

    @classmethod
    def from_bounded_context(cls, bc: BoundedContext) -> BoundedContextDoc:
        doc = cls(name=bc.name)

        for root_cls in bc.aggregate_roots:
            doc.roots.append(
                RootEntityDoc.from_root_entity(root_cls, bc.contracts_by_root.get(root_cls))
            )

        for ent_cls in bc.entities:
            doc.entities.append(EntityDoc.from_entity(ent_cls))

        for vo_cls in bc.value_objects:
            doc.value_objects.append(ValueObjectDoc.from_value_object(vo_cls))

        for svc_cls in bc.services:
            doc.services.append(ServiceDoc.from_service(svc_cls))

        for uc_cls in bc.use_cases:
            doc.use_cases.append(UseCaseDoc.from_use_case(uc_cls))

        return doc
