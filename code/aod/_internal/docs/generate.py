from __future__ import annotations

from pathlib import Path
from typing import Any

from aod._internal.application.contracts import Command, Query
from aod._internal.application.port import Port
from aod._internal.application.use_case import UseCase
from aod._internal.core.event_emitter import Event
from aod._internal.domain.bounded_context import BoundedContext

from .introspect import (
    introspect_bounded_context,
    introspect_command,
    introspect_event,
    introspect_exception,
    introspect_handler,
    introspect_port,
    introspect_projection,
    introspect_query,
    introspect_session,
    introspect_use_case,
    _make_type_doc,
)
from .model import (
    AppDoc,
    ContextDoc,
    DocApp,
    DocInfra,
    EventDoc,
    ExceptionDoc,
    HandlerDoc,
    PortDoc,
    ProjectionDoc,
    SessionDoc,
    TypeDoc,
    UseCaseDoc,
)
from .renderer import (
    render_api_index,
    render_application_commands,
    render_application_index,
    render_application_ports,
    render_application_queries,
    render_application_use_cases,
    render_command,
    render_context,
    render_domain_entities,
    render_domain_events,
    render_domain_index,
    render_domain_services,
    render_domain_value_objects,
    render_entity,
    render_exceptions,
    render_handler,
    render_home,
    render_infrastructure_handlers,
    render_infrastructure_implementations,
    render_infrastructure_index,
    render_infrastructure_projections,
    render_port,
    render_projection,
    render_query,
    render_service,
    render_use_case,
    render_value_object,
)
from .zensical import generate_zensical_toml


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _collect_events_from_types(
    contexts: list[BoundedContext],
) -> list[EventDoc]:
    import typing

    seen: set[str] = set()
    result: list[EventDoc] = []
    for ctx in contexts:
        all_types = list(ctx.aggregate_roots) + list(ctx.entities) + list(ctx.value_objects) + list(ctx.services)
        for cls in all_types:
            hints: dict[str, Any] = {}
            try:
                hints = {k: v for k, v in typing.get_type_hints(cls).items() if not k.startswith("_")}
            except Exception:
                pass
            for field_name, field_type in hints.items():
                resolved = field_type
                origin = typing.get_origin(resolved)
                if origin is not None:
                    args = typing.get_args(resolved)
                    for arg in args:
                        if isinstance(arg, type) and issubclass(arg, Event) and arg.__name__ not in seen:
                            seen.add(arg.__name__)
                            result.append(introspect_event(arg))
                elif isinstance(resolved, type) and issubclass(resolved, Event) and resolved.__name__ not in seen:
                    seen.add(resolved.__name__)
                    result.append(introspect_event(resolved))
    return result


def _collect_exceptions(infra: DocInfra) -> list[ExceptionDoc]:
    result: list[ExceptionDoc] = []
    for exc_cls in infra.exceptions:
        if isinstance(exc_cls, type) and issubclass(exc_cls, BaseException):
            result.append(introspect_exception(exc_cls))
    return result


def _collect_sessions(infra: DocInfra) -> list[SessionDoc]:
    result: list[SessionDoc] = []
    for sess_cls in infra.sessions:
        if isinstance(sess_cls, type):
            result.append(introspect_session(sess_cls))
    return result


def _collect_handlers(infra: DocInfra) -> list[HandlerDoc]:
    result: list[HandlerDoc] = []
    for handler_cls in infra.handlers:
        if isinstance(handler_cls, type):
            result.append(introspect_handler(handler_cls))
    return result


def _collect_projections(infra: DocInfra) -> list[ProjectionDoc]:
    result: list[ProjectionDoc] = []
    for proj_cls in infra.projections:
        if isinstance(proj_cls, type):
            result.append(introspect_projection(proj_cls))
    return result


def _collect_port_impls(infra: DocInfra) -> list[TypeDoc]:
    result: list[TypeDoc] = []
    for impl_cls in infra.port_impls:
        if isinstance(impl_cls, type):
            result.append(_make_type_doc(impl_cls, "Implementation"))
    return result


def _build_app_doc(app: DocApp) -> AppDoc:
    contexts: list[ContextDoc] = []
    for ctx in app.bounded_contexts:
        if isinstance(ctx, BoundedContext):
            contexts.append(introspect_bounded_context(ctx))

    _collect_events_from_types(app.bounded_contexts)

    use_cases: list[UseCaseDoc] = []
    for uc_cls in app.use_cases:
        if isinstance(uc_cls, type) and issubclass(uc_cls, UseCase):
            use_cases.append(introspect_use_case(uc_cls))

    commands: list = []
    for cmd_cls in app.commands:
        if isinstance(cmd_cls, type) and issubclass(cmd_cls, Command):
            commands.append(introspect_command(cmd_cls))

    queries: list = []
    for q_cls in app.queries:
        if isinstance(q_cls, type) and issubclass(q_cls, Query):
            queries.append(introspect_query(q_cls))

    ports: list[PortDoc] = []
    for port_cls in app.ports:
        if isinstance(port_cls, type) and issubclass(port_cls, Port):
            ports.append(introspect_port(port_cls))

    sessions = _collect_sessions(app.infra)
    handlers = _collect_handlers(app.infra)
    projections = _collect_projections(app.infra)
    port_impls = _collect_port_impls(app.infra)
    exceptions = _collect_exceptions(app.infra)

    return AppDoc(
        name=app.name,
        description=app.description,
        version=app.version,
        repo_url=app.repo_url,
        contexts=contexts,
        use_cases=use_cases,
        commands=commands,
        queries=queries,
        ports=ports,
        sessions=sessions,
        handlers=handlers,
        projections=projections,
        port_impls=port_impls,
        exceptions=exceptions,
    )


def generate_docs(apps: list[DocApp], output_dir: str = "site-docs") -> Path:
    root = Path(output_dir)
    docs = root / "docs"
    app_docs = [_build_app_doc(app) for app in apps]

    _write_file(docs / "index.md", render_home(app_docs))

    toml_content = generate_zensical_toml(app_docs)
    _write_file(root / "zensical.toml", toml_content)

    _write_file(docs / "api" / "index.md", render_api_index(app_docs))

    for app_doc in app_docs:
        app_slug = _slug(app_doc.name)
        app_dir = docs / app_slug

        _write_file(app_dir / "index.md", render_home([app_doc]))
        _write_file(app_dir / "domain" / "index.md", render_domain_index(app_doc))
        _write_file(app_dir / "domain" / "entities.md", render_domain_entities(app_doc))
        _write_file(app_dir / "domain" / "value-objects.md", render_domain_value_objects(app_doc))
        _write_file(app_dir / "domain" / "services.md", render_domain_services(app_doc))
        _write_file(app_dir / "domain" / "events.md", render_domain_events(app_doc))

        for ctx in app_doc.contexts:
            ctx_slug = _slug(ctx.name)
            _write_file(app_dir / "domain" / f"{ctx_slug}.md", render_context(ctx))

        for entity in [
            e
            for ctx in app_doc.contexts
            for e in ctx.aggregate_roots + ctx.entities
        ]:
            _write_file(app_dir / "domain" / f"{_slug(entity.name)}.md", render_entity(entity))

        for vo in [v for ctx in app_doc.contexts for v in ctx.value_objects]:
            _write_file(app_dir / "domain" / f"{_slug(vo.name)}.md", render_value_object(vo))

        for svc in [s for ctx in app_doc.contexts for s in ctx.services]:
            _write_file(app_dir / "domain" / f"{_slug(svc.name)}.md", render_service(svc))

        _write_file(app_dir / "application" / "index.md", render_application_index(app_doc))
        _write_file(app_dir / "application" / "use-cases.md", render_application_use_cases(app_doc))
        _write_file(app_dir / "application" / "commands.md", render_application_commands(app_doc))
        _write_file(app_dir / "application" / "queries.md", render_application_queries(app_doc))
        _write_file(app_dir / "application" / "ports.md", render_application_ports(app_doc))

        for uc in app_doc.use_cases:
            _write_file(app_dir / "application" / f"{_slug(uc.name)}.md", render_use_case(uc))

        for cmd in app_doc.commands:
            _write_file(app_dir / "application" / f"{_slug(cmd.name)}.md", render_command(cmd))

        for q in app_doc.queries:
            _write_file(app_dir / "application" / f"{_slug(q.name)}.md", render_query(q))

        for p in app_doc.ports:
            _write_file(app_dir / "application" / f"{_slug(p.name)}.md", render_port(p))

        _write_file(app_dir / "infrastructure" / "index.md", render_infrastructure_index(app_doc))
        _write_file(app_dir / "infrastructure" / "handlers.md", render_infrastructure_handlers(app_doc))
        _write_file(
            app_dir / "infrastructure" / "projections.md",
            render_infrastructure_projections(app_doc),
        )
        _write_file(
            app_dir / "infrastructure" / "implementations.md",
            render_infrastructure_implementations(app_doc),
        )

        for h in app_doc.handlers:
            _write_file(app_dir / "infrastructure" / f"{_slug(h.name)}.md", render_handler(h))

        for proj in app_doc.projections:
            _write_file(app_dir / "infrastructure" / f"{_slug(proj.name)}.md", render_projection(proj))

        for pi in app_doc.port_impls:
            _write_file(app_dir / "infrastructure" / f"{_slug(pi.name)}.md", render_port(pi))

        _write_file(app_dir / "exceptions.md", render_exceptions(app_doc))

    return root
