from __future__ import annotations

import inspect
from typing import Any

from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler.handler import HandlerProtocol
from aod._internal.core.fields import is_public_field
from aod._internal.core.type_checking.extractors import extract_types_from_annotation
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases
from aod._internal.core.type_utils import type_name
from aod._internal.domain.entity import RootEntity
from aod._internal.infrastructure.handlers.handlers import AsyncBaseHandler, BaseHandler
from aod._internal.infrastructure.projection.projection import (
    ReadProjectionBase,
    WriteProjectionBase,
)

from .model import (
    ContractDoc,
    ContextDoc,
    EntityDoc,
    EventDoc,
    ExceptionDoc,
    FieldDoc,
    HandlerDoc,
    MethodDoc,
    ParamDoc,
    PortDoc,
    ProjectionDoc,
    ServiceDoc,
    SessionDoc,
    TypeDoc,
    UseCaseDoc,
    ValueObjectDoc,
)


def _extract_description(field_info: Any) -> str:
    return getattr(field_info, "description", None) or ""


def _extract_fields(cls: type) -> list[FieldDoc]:
    fields = getattr(cls, "__model_fields__", None)
    if fields is None:
        return []

    result: list[FieldDoc] = []
    for name, field_info in fields.items():
        if not is_public_field(name):
            continue
        annotation = getattr(field_info, "annotation", None)
        if annotation is None:
            continue
        types = [t for t in extract_types_from_annotation(annotation) if isinstance(t, type)]
        result.append(
            FieldDoc(
                name=name,
                type_name=type_name(annotation),
                description=_extract_description(field_info),
                types=types,
            )
        )
    return result


def _extract_params(func: Any) -> tuple[list[ParamDoc], str]:
    try:
        sig = inspect.signature(func)
    except ValueError, TypeError:
        return [], ""
    params: list[ParamDoc] = []
    for pname, p in sig.parameters.items():
        if pname in ("self", "cls"):
            continue
        ptype = type_name(p.annotation) if p.annotation is not inspect.Parameter.empty else ""
        params.append(ParamDoc(name=pname, type_name=ptype))
    returns = (
        type_name(sig.return_annotation)
        if sig.return_annotation is not inspect.Signature.empty
        else ""
    )
    return params, returns


def _extract_methods(cls: type) -> list[MethodDoc]:
    result: list[MethodDoc] = []
    for name in sorted(cls.__dict__):
        if not is_public_field(name):
            continue
        val = cls.__dict__[name]
        if not callable(val):
            continue
        try:
            sig_str = str(inspect.signature(val))
            params, returns = _extract_params(val)
        except ValueError, TypeError:
            sig_str = "(...)"
            params = []
            returns = ""
        doc = inspect.getdoc(val) or ""
        result.append(
            MethodDoc(name=name, signature=sig_str, doc=doc, params=params, returns=returns)
        )
    return result


def _get_own_doc(cls: type) -> str:
    doc = cls.__doc__ or ""
    if not doc:
        return ""
    for base in cls.__mro__[1:]:
        if base.__doc__ == doc:
            continue
        return doc
    if cls.__doc__ and cls.__doc__ != cls.__mro__[1].__doc__ if len(cls.__mro__) > 1 else True:
        return doc
    return ""


def _make_type_doc(cls: type, stereotype: str) -> TypeDoc:
    return TypeDoc(
        name=cls.__name__,
        stereotype=stereotype,
        doc=_get_own_doc(cls),
        fields=_extract_fields(cls),
        methods=_extract_methods(cls),
    )


def introspect_entity(cls: type) -> EntityDoc:
    td = _make_type_doc(cls, "RootEntity" if issubclass(cls, RootEntity) else "Entity")
    return EntityDoc(
        name=td.name,
        stereotype=td.stereotype,
        doc=td.doc,
        fields=td.fields,
        methods=td.methods,
    )


def introspect_value_object(cls: type) -> ValueObjectDoc:
    td = _make_type_doc(cls, "ValueObject")
    return ValueObjectDoc(
        name=td.name,
        stereotype=td.stereotype,
        doc=td.doc,
        fields=td.fields,
        methods=td.methods,
    )


def introspect_service(cls: type) -> ServiceDoc:
    td = _make_type_doc(cls, "Service")
    return ServiceDoc(
        name=td.name,
        stereotype=td.stereotype,
        doc=td.doc,
        fields=td.fields,
        methods=td.methods,
    )


def introspect_event(cls: type) -> EventDoc:
    td = _make_type_doc(cls, "Event")
    return EventDoc(
        name=td.name,
        stereotype=td.stereotype,
        doc=td.doc,
        fields=td.fields,
        methods=td.methods,
    )


def introspect_port(cls: type) -> PortDoc:
    td = _make_type_doc(cls, "Port")
    return PortDoc(
        name=td.name,
        stereotype=td.stereotype,
        doc=td.doc,
        fields=td.fields,
        methods=td.methods,
    )


def _extract_contract_generic(cls: type, origin: type) -> tuple[str, str]:
    entity_type = get_generic_arg_from_orig_bases(cls, origin, index=0)
    result_type = get_generic_arg_from_orig_bases(cls, origin, index=1)
    return (
        type_name(entity_type) if entity_type is not None else "",
        type_name(result_type) if result_type is not None else "",
    )


def introspect_command(cls: type) -> ContractDoc:
    td = _make_type_doc(cls, "Command")
    entity_type, result_type = _extract_contract_generic(cls, Command)
    return ContractDoc(
        name=td.name,
        stereotype=td.stereotype,
        doc=td.doc,
        fields=td.fields,
        methods=td.methods,
        entity_type=entity_type,
        result_type=result_type,
    )


def introspect_query(cls: type) -> ContractDoc:
    td = _make_type_doc(cls, "Query")
    entity_type, result_type = _extract_contract_generic(cls, Query)
    return ContractDoc(
        name=td.name,
        stereotype=td.stereotype,
        doc=td.doc,
        fields=td.fields,
        methods=td.methods,
        entity_type=entity_type,
        result_type=result_type,
    )


_AUTO_WIRED_PORT_NAMES = frozenset({"uow", "logger", "event_bus", "cache"})


def _get_original_run(cls: type) -> Any:
    run_method = cls.__dict__.get("run")
    if run_method is None:
        return None
    original = getattr(run_method, "__wrapped__", None)
    if original is not None:
        return original
    for base in cls.__mro__:
        if base is cls:
            continue
        if "run" in base.__dict__:
            base_run = base.__dict__["run"]
            return getattr(base_run, "__wrapped__", base_run)
    return run_method


def introspect_use_case(cls: type) -> UseCaseDoc:
    td = _make_type_doc(cls, "UseCase")

    run_method = _get_original_run(cls)
    run_params: list[ParamDoc] = []
    run_returns = ""
    run_doc = ""
    if run_method is not None:
        run_params, run_returns = _extract_params(run_method)
        run_doc = inspect.getdoc(run_method) or ""

    all_fields = _extract_fields(cls)
    port_fields = [f for f in all_fields if f.name not in _AUTO_WIRED_PORT_NAMES]

    combined_doc = td.doc
    if run_doc:
        if combined_doc:
            combined_doc = f"{combined_doc}\n\n{run_doc}"
        else:
            combined_doc = run_doc

    return UseCaseDoc(
        name=td.name,
        stereotype=td.stereotype,
        doc=combined_doc,
        fields=td.fields,
        methods=td.methods,
        run_params=run_params,
        run_returns=run_returns,
        port_fields=port_fields,
    )


def introspect_handler(cls: type) -> HandlerDoc:
    td = _make_type_doc(cls, "Handler")

    contract_type = ""
    if issubclass(cls, (BaseHandler, AsyncBaseHandler)):
        for origin_cls in (BaseHandler, AsyncBaseHandler):
            contract_type_obj = get_generic_arg_from_orig_bases(cls, origin_cls, index=0)
            if contract_type_obj is not None:
                contract_type = type_name(contract_type_obj)
                break
    if not contract_type:
        contract_type_obj = get_generic_arg_from_orig_bases(cls, HandlerProtocol, index=0)
        if contract_type_obj is not None:
            contract_type = type_name(contract_type_obj)

    handle_method = cls.__dict__.get("handle")
    handle_params: list[ParamDoc] = []
    handle_returns = ""
    if handle_method is not None:
        handle_params, handle_returns = _extract_params(handle_method)

    return HandlerDoc(
        name=td.name,
        stereotype=td.stereotype,
        doc=td.doc,
        fields=td.fields,
        methods=td.methods,
        contract_type=contract_type,
        handle_params=handle_params,
        handle_returns=handle_returns,
    )


def introspect_projection(cls: type) -> ProjectionDoc:
    td = _make_type_doc(cls, "Projection")

    method_name = ""
    method_params: list[ParamDoc] = []
    method_returns = ""
    model_type = ""

    for candidate_name, model_cls in [("read", ReadProjectionBase), ("write", WriteProjectionBase)]:
        if issubclass(cls, model_cls) and candidate_name in cls.__dict__:
            method_name = candidate_name
            method_obj = cls.__dict__[candidate_name]
            method_params, method_returns = _extract_params(method_obj)
            if method_params:
                model_type = method_params[0].type_name
            break

    return ProjectionDoc(
        name=td.name,
        stereotype=td.stereotype,
        doc=td.doc,
        fields=td.fields,
        methods=td.methods,
        model_type=model_type,
        method_name=method_name,
        method_params=method_params,
        method_returns=method_returns,
    )


def introspect_session(cls: type) -> SessionDoc:
    td = _make_type_doc(cls, "Session")
    return SessionDoc(
        name=td.name,
        stereotype=td.stereotype,
        doc=td.doc,
        fields=td.fields,
        methods=td.methods,
    )


def introspect_exception(cls: type) -> ExceptionDoc:
    bases = cls.__bases__
    base_name = bases[0].__name__ if bases else ""
    return ExceptionDoc(
        name=cls.__name__,
        base=base_name,
        doc=inspect.getdoc(cls) or "",
    )


def introspect_bounded_context(ctx: Any) -> ContextDoc:
    aggregate_roots = [introspect_entity(cls) for cls in ctx.aggregate_roots]
    entities = [introspect_entity(cls) for cls in ctx.entities]
    value_objects = [introspect_value_object(cls) for cls in ctx.value_objects]
    services = [introspect_service(cls) for cls in ctx.services]
    return ContextDoc(
        name=ctx.name or repr(ctx),
        doc=inspect.getdoc(type(ctx)) or "",
        aggregate_roots=aggregate_roots,
        entities=entities,
        value_objects=value_objects,
        services=services,
    )
