from __future__ import annotations

import inspect
from dataclasses import dataclass, field

from aod._internal.domain.service import Service
from aod._internal.schema.describe_utils import extract_methods
from aod._internal.schema.docs.generic_docs import MethodDoc


@dataclass
class ServiceDoc:
    name: str
    description: str = ""
    methods: list[MethodDoc] = field(default_factory=list)

    @classmethod
    def from_service(cls, svc_cls: type[Service]) -> ServiceDoc:
        return cls(
            name=svc_cls.__name__,
            description=inspect.getdoc(svc_cls) or "",
            methods=extract_methods(svc_cls),
        )
