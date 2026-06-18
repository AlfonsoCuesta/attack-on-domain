from __future__ import annotations

from dataclasses import dataclass, field

from aod._internal.schema.docs.handler_doc import HandlerDoc
from aod._internal.schema.docs.port_doc import PortDoc
from aod._internal.schema.docs.projection_doc import ProjectionDoc
from aod._internal.schema.docs.session_doc import SessionDoc
from aod._internal.schema.infrastructure import Infrastructure


@dataclass
class InfrastructureDoc:
    handlers: list[HandlerDoc] = field(default_factory=list)
    sessions: list[SessionDoc] = field(default_factory=list)
    projections: list[ProjectionDoc] = field(default_factory=list)
    ports: list[PortDoc] = field(default_factory=list)

    @classmethod
    def from_infrastructure(cls, infra: Infrastructure) -> InfrastructureDoc:
        return cls(
            handlers=[HandlerDoc.from_handler(h) for h in infra.handlers],
            sessions=[SessionDoc.from_session(s) for s in infra.sessions],
            projections=[ProjectionDoc.from_projection(p) for p in infra.projections],
            ports=[PortDoc.from_port(p) for p in infra.ports],
        )
