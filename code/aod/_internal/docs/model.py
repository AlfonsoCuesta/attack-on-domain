from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocInfra:
    sessions: list[Any] = field(default_factory=list)
    handlers: list[Any] = field(default_factory=list)
    projections: list[Any] = field(default_factory=list)
    port_impls: list[Any] = field(default_factory=list)
    exceptions: list[Any] = field(default_factory=list)


@dataclass
class DocApp:
    name: str
    description: str
    version: str = "0.1.0"
    repo_url: str | None = None
    bounded_contexts: list[Any] = field(default_factory=list)
    use_cases: list[Any] = field(default_factory=list)
    commands: list[Any] = field(default_factory=list)
    queries: list[Any] = field(default_factory=list)
    ports: list[Any] = field(default_factory=list)
    infra: DocInfra = field(default_factory=DocInfra)


@dataclass
class FieldDoc:
    name: str
    type_name: str
    description: str = ""
    types: list[type] = field(default_factory=list)


@dataclass
class ParamDoc:
    name: str
    type_name: str


@dataclass
class MethodDoc:
    name: str
    signature: str
    doc: str
    params: list[ParamDoc] = field(default_factory=list)
    returns: str = ""


@dataclass
class TypeDoc:
    name: str
    stereotype: str
    doc: str
    fields: list[FieldDoc] = field(default_factory=list)
    methods: list[MethodDoc] = field(default_factory=list)


@dataclass
class EntityDoc(TypeDoc):
    pass


@dataclass
class ValueObjectDoc(TypeDoc):
    pass


@dataclass
class ServiceDoc(TypeDoc):
    pass


@dataclass
class EventDoc(TypeDoc):
    pass


@dataclass
class ContractDoc(TypeDoc):
    entity_type: str = ""
    result_type: str = ""


@dataclass
class UseCaseDoc(TypeDoc):
    run_params: list[ParamDoc] = field(default_factory=list)
    run_returns: str = ""
    port_fields: list[FieldDoc] = field(default_factory=list)


@dataclass
class PortDoc(TypeDoc):
    pass


@dataclass
class HandlerDoc(TypeDoc):
    contract_type: str = ""
    handle_params: list[ParamDoc] = field(default_factory=list)
    handle_returns: str = ""


@dataclass
class ProjectionDoc(TypeDoc):
    model_type: str = ""
    method_name: str = ""
    method_params: list[ParamDoc] = field(default_factory=list)
    method_returns: str = ""


@dataclass
class SessionDoc(TypeDoc):
    pass


@dataclass
class ExceptionDoc:
    name: str
    base: str
    doc: str


@dataclass
class ContextDoc:
    name: str
    doc: str
    aggregate_roots: list[EntityDoc]
    entities: list[EntityDoc]
    value_objects: list[ValueObjectDoc]
    services: list[ServiceDoc]


@dataclass
class AppDoc:
    name: str
    description: str
    version: str
    repo_url: str | None
    contexts: list[ContextDoc]
    use_cases: list[UseCaseDoc]
    commands: list[ContractDoc]
    queries: list[ContractDoc]
    ports: list[PortDoc]
    sessions: list[SessionDoc]
    handlers: list[HandlerDoc]
    projections: list[ProjectionDoc]
    port_impls: list[TypeDoc]
    exceptions: list[ExceptionDoc]
