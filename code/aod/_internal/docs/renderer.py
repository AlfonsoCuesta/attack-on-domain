from __future__ import annotations


from .model import (
    AppDoc,
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
    UseCaseDoc,
    ValueObjectDoc,
)


def _escape_code(text: str) -> str:
    return text.replace("[", "\\[").replace("]", "\\]")


def _field_row(f: FieldDoc) -> str:
    desc = f.description if f.description else "--"
    return f"| `{f.name}` | `{f.type_name}` | {desc} |"


def _param_row(p: ParamDoc) -> str:
    return f"| `{p.name}` | `{p.type_name}` |"


def _fields_table(fields: list[FieldDoc]) -> str:
    if not fields:
        return ""
    lines = ["| Field | Type | Description |", "| --- | --- | --- |"]
    lines.extend(_field_row(f) for f in fields)
    return "\n".join(lines)


def _methods_section(methods: list[MethodDoc], skip: set[str] | None = None) -> str:
    skip = skip or set()
    parts: list[str] = []
    for m in methods:
        if m.name in skip:
            continue
        sig = _escape_code(m.signature)
        parts.append(f"### `{m.name}{sig}`\n")
        if m.doc:
            doc = _escape_code(m.doc)
            parts.append(f"{doc}\n")
        if m.params:
            parts.append("| Parameter | Type |")
            parts.append("| --- | --- |")
            parts.extend(_param_row(p) for p in m.params)
            parts.append("")
        if m.returns:
            parts.append(f"**Returns:** `{m.returns}`\n")
    return "\n".join(parts)


def render_entity(e: EntityDoc) -> str:
    lines = [f"# {e.name}\n"]
    if e.doc:
        lines.append(f"{e.doc}\n")
    lines.append(f"**Stereotype:** {e.stereotype}\n")
    if e.fields:
        lines.append("## Fields\n")
        lines.append(_fields_table(e.fields))
        lines.append("")
    if e.methods:
        lines.append("## Methods\n")
        lines.append(_methods_section(e.methods, skip={"__init__"}))
    return "\n".join(lines)


def render_value_object(vo: ValueObjectDoc) -> str:
    lines = [f"# {vo.name}\n"]
    if vo.doc:
        lines.append(f"{vo.doc}\n")
    lines.append(f"**Stereotype:** {vo.stereotype}\n")
    if vo.fields:
        lines.append("## Fields\n")
        lines.append(_fields_table(vo.fields))
        lines.append("")
    if vo.methods:
        lines.append("## Methods\n")
        lines.append(_methods_section(vo.methods, skip={"__init__"}))
    return "\n".join(lines)


def render_service(s: ServiceDoc) -> str:
    lines = [f"# {s.name}\n"]
    if s.doc:
        lines.append(f"{s.doc}\n")
    lines.append(f"**Stereotype:** {s.stereotype}\n")
    if s.fields:
        lines.append("## Fields\n")
        lines.append(_fields_table(s.fields))
        lines.append("")
    if s.methods:
        lines.append("## Methods\n")
        lines.append(_methods_section(s.methods, skip={"__init__"}))
    return "\n".join(lines)


def render_event(ev: EventDoc) -> str:
    lines = [f"# {ev.name}\n"]
    if ev.doc:
        lines.append(f"{ev.doc}\n")
    lines.append(f"**Stereotype:** {ev.stereotype}\n")
    if ev.fields:
        lines.append("## Fields\n")
        lines.append(_fields_table(ev.fields))
        lines.append("")
    if ev.methods:
        lines.append("## Methods\n")
        lines.append(_methods_section(ev.methods))
    return "\n".join(lines)


def render_port(p: PortDoc) -> str:
    lines = [f"# {p.name}\n"]
    if p.doc:
        lines.append(f"{p.doc}\n")
    lines.append(f"**Stereotype:** {p.stereotype}\n")
    if p.fields:
        lines.append("## Fields\n")
        lines.append(_fields_table(p.fields))
        lines.append("")
    if p.methods:
        lines.append("## Methods\n")
        lines.append(_methods_section(p.methods))
    return "\n".join(lines)


def render_command(c: ContractDoc) -> str:
    lines = [f"# {c.name}\n"]
    if c.doc:
        lines.append(f"{c.doc}\n")
    lines.append(f"**Stereotype:** {c.stereotype}\n")
    if c.entity_type:
        lines.append(f"**Entity Type:** `{c.entity_type}`\n")
    if c.result_type:
        lines.append(f"**Result Type:** `{c.result_type}`\n")
    if c.fields:
        lines.append("## Fields\n")
        lines.append(_fields_table(c.fields))
        lines.append("")
    if c.methods:
        lines.append("## Methods\n")
        lines.append(_methods_section(c.methods))
    return "\n".join(lines)


def render_query(q: ContractDoc) -> str:
    lines = [f"# {q.name}\n"]
    if q.doc:
        lines.append(f"{q.doc}\n")
    lines.append(f"**Stereotype:** {q.stereotype}\n")
    if q.entity_type:
        lines.append(f"**Entity Type:** `{q.entity_type}`\n")
    if q.result_type:
        lines.append(f"**Result Type:** `{q.result_type}`\n")
    if q.fields:
        lines.append("## Fields\n")
        lines.append(_fields_table(q.fields))
        lines.append("")
    if q.methods:
        lines.append("## Methods\n")
        lines.append(_methods_section(q.methods))
    return "\n".join(lines)


def render_use_case(uc: UseCaseDoc) -> str:
    lines = [f"# {uc.name}\n"]
    if uc.doc:
        lines.append(f"{uc.doc}\n")
    lines.append(f"**Stereotype:** {uc.stereotype}\n")
    if uc.port_fields:
        lines.append("## Port Fields\n")
        lines.append(_fields_table(uc.port_fields))
        lines.append("")
    if uc.run_params:
        lines.append("## `run()` Parameters\n")
        lines.append("| Parameter | Type |")
        lines.append("| --- | --- |")
        lines.extend(_param_row(p) for p in uc.run_params)
        lines.append("")
    if uc.run_returns:
        lines.append(f"**Returns:** `{uc.run_returns}`\n")
    if uc.fields:
        lines.append("## All Fields\n")
        lines.append(_fields_table(uc.fields))
        lines.append("")
    if uc.methods:
        lines.append("## Methods\n")
        lines.append(_methods_section(uc.methods, skip={"run"}))
    return "\n".join(lines)


def render_handler(h: HandlerDoc) -> str:
    lines = [f"# {h.name}\n"]
    if h.doc:
        lines.append(f"{h.doc}\n")
    lines.append(f"**Stereotype:** {h.stereotype}\n")
    if h.contract_type:
        lines.append(f"**Contract:** `{h.contract_type}`\n")
    if h.handle_params:
        lines.append("## `handle()` Parameters\n")
        lines.append("| Parameter | Type |")
        lines.append("| --- | --- |")
        lines.extend(_param_row(p) for p in h.handle_params)
        lines.append("")
    if h.handle_returns:
        lines.append(f"**Returns:** `{h.handle_returns}`\n")
    if h.fields:
        lines.append("## Fields\n")
        lines.append(_fields_table(h.fields))
        lines.append("")
    if h.methods:
        lines.append("## Methods\n")
        lines.append(_methods_section(h.methods, skip={"handle"}))
    return "\n".join(lines)


def render_projection(proj: ProjectionDoc) -> str:
    lines = [f"# {proj.name}\n"]
    if proj.doc:
        lines.append(f"{proj.doc}\n")
    lines.append(f"**Stereotype:** {proj.stereotype}\n")
    if proj.method_name:
        lines.append(f"**Method:** `{proj.method_name}`\n")
    if proj.model_type:
        lines.append(f"**Model Type:** `{proj.model_type}`\n")
    if proj.method_params:
        lines.append(f"## `{proj.method_name}()` Parameters\n")
        lines.append("| Parameter | Type |")
        lines.append("| --- | --- |")
        lines.extend(_param_row(p) for p in proj.method_params)
        lines.append("")
    if proj.method_returns:
        lines.append(f"**Returns:** `{proj.method_returns}`\n")
    if proj.fields:
        lines.append("## Fields\n")
        lines.append(_fields_table(proj.fields))
        lines.append("")
    if proj.methods:
        lines.append("## Methods\n")
        lines.append(_methods_section(proj.methods, skip={"read", "write"}))
    return "\n".join(lines)


def render_session(s: SessionDoc) -> str:
    lines = [f"# {s.name}\n"]
    if s.doc:
        lines.append(f"{s.doc}\n")
    lines.append(f"**Stereotype:** {s.stereotype}\n")
    if s.fields:
        lines.append("## Fields\n")
        lines.append(_fields_table(s.fields))
        lines.append("")
    if s.methods:
        lines.append("## Methods\n")
        lines.append(_methods_section(s.methods))
    return "\n".join(lines)


def render_exception(ex: ExceptionDoc) -> str:
    lines = [f"# {ex.name}\n"]
    if ex.doc:
        lines.append(f"{ex.doc}\n")
    if ex.base:
        lines.append(f"**Base:** `{ex.base}`\n")
    return "\n".join(lines)


def render_context(ctx: ContextDoc) -> str:
    lines = [f"# {ctx.name}\n"]
    if ctx.doc:
        lines.append(f"{ctx.doc}\n")
    if ctx.aggregate_roots:
        lines.append("## Aggregate Roots\n")
        for ar in ctx.aggregate_roots:
            lines.append(f"- [{ar.name}]({ar.name.lower()}.md)")
        lines.append("")
    if ctx.entities:
        lines.append("## Entities\n")
        for ent in ctx.entities:
            lines.append(f"- [{ent.name}]({ent.name.lower()}.md)")
        lines.append("")
    if ctx.value_objects:
        lines.append("## Value Objects\n")
        for vo in ctx.value_objects:
            lines.append(f"- [{vo.name}]({vo.name.lower()}.md)")
        lines.append("")
    if ctx.services:
        lines.append("## Services\n")
        for svc in ctx.services:
            lines.append(f"- [{svc.name}]({svc.name.lower()}.md)")
        lines.append("")
    return "\n".join(lines)


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def render_domain_index(app: AppDoc) -> str:
    lines = [f"# {app.name} - Domain\n"]
    if app.contexts:
        lines.append("## Bounded Contexts\n")
        for ctx in app.contexts:
            lines.append(f"- [{ctx.name}]({_slug(ctx.name)}.md)")
        lines.append("")
    all_entities = []
    all_vos = []
    for ctx in app.contexts:
        all_entities.extend(ctx.aggregate_roots)
        all_entities.extend(ctx.entities)
        all_vos.extend(ctx.value_objects)
    if all_entities:
        lines.append("## All Entities\n")
        for e in all_entities:
            lines.append(f"- [{e.name}]({_slug(e.name)}.md)")
        lines.append("")
    if all_vos:
        lines.append("## All Value Objects\n")
        for vo in all_vos:
            lines.append(f"- [{vo.name}]({_slug(vo.name)}.md)")
        lines.append("")
    return "\n".join(lines)


def render_domain_entities(app: AppDoc) -> str:
    lines = ["# Entities\n"]
    all_entities: list[EntityDoc] = []
    for ctx in app.contexts:
        all_entities.extend(ctx.aggregate_roots)
        all_entities.extend(ctx.entities)
    for e in all_entities:
        lines.append(render_entity(e))
        lines.append("---\n")
    return "\n".join(lines)


def render_domain_value_objects(app: AppDoc) -> str:
    lines = ["# Value Objects\n"]
    all_vos: list[ValueObjectDoc] = []
    for ctx in app.contexts:
        all_vos.extend(ctx.value_objects)
    for vo in all_vos:
        lines.append(render_value_object(vo))
        lines.append("---\n")
    return "\n".join(lines)


def render_domain_services(app: AppDoc) -> str:
    lines = ["# Services\n"]
    all_svcs: list[ServiceDoc] = []
    for ctx in app.contexts:
        all_svcs.extend(ctx.services)
    for s in all_svcs:
        lines.append(render_service(s))
        lines.append("---\n")
    return "\n".join(lines)


def render_domain_events(app: AppDoc) -> str:
    lines = ["# Domain Events\n"]
    for ctx in app.contexts:
        all_types = list(ctx.aggregate_roots) + list(ctx.entities) + list(ctx.value_objects) + list(ctx.services)
        for td in all_types:
            for method in td.methods:
                if method.name == "emit":
                    lines.append(f"- **{td.name}**")
    lines.append("")
    return "\n".join(lines)


def render_application_index(app: AppDoc) -> str:
    lines = [f"# {app.name} - Application\n"]
    if app.use_cases:
        lines.append("## Use Cases\n")
        for uc in app.use_cases:
            lines.append(f"- [{uc.name}]({_slug(uc.name)}.md)")
        lines.append("")
    if app.commands:
        lines.append("## Commands\n")
        for cmd in app.commands:
            lines.append(f"- [{cmd.name}]({_slug(cmd.name)}.md)")
        lines.append("")
    if app.queries:
        lines.append("## Queries\n")
        for q in app.queries:
            lines.append(f"- [{q.name}]({_slug(q.name)}.md)")
        lines.append("")
    if app.ports:
        lines.append("## Ports\n")
        for p in app.ports:
            lines.append(f"- [{p.name}]({_slug(p.name)}.md)")
        lines.append("")
    return "\n".join(lines)


def render_application_use_cases(app: AppDoc) -> str:
    lines = ["# Use Cases\n"]
    for uc in app.use_cases:
        lines.append(render_use_case(uc))
        lines.append("---\n")
    return "\n".join(lines)


def render_application_commands(app: AppDoc) -> str:
    lines = ["# Commands\n"]
    for cmd in app.commands:
        lines.append(render_command(cmd))
        lines.append("---\n")
    return "\n".join(lines)


def render_application_queries(app: AppDoc) -> str:
    lines = ["# Queries\n"]
    for q in app.queries:
        lines.append(render_query(q))
        lines.append("---\n")
    return "\n".join(lines)


def render_application_ports(app: AppDoc) -> str:
    lines = ["# Ports\n"]
    for p in app.ports:
        lines.append(render_port(p))
        lines.append("---\n")
    return "\n".join(lines)


def render_infrastructure_index(app: AppDoc) -> str:
    lines = [f"# {app.name} - Infrastructure\n"]
    if app.handlers:
        lines.append("## Handlers\n")
        for h in app.handlers:
            lines.append(f"- [{h.name}]({_slug(h.name)}.md)")
        lines.append("")
    if app.projections:
        lines.append("## Projections\n")
        for proj in app.projections:
            lines.append(f"- [{proj.name}]({_slug(proj.name)}.md)")
        lines.append("")
    if app.port_impls:
        lines.append("## Port Implementations\n")
        for pi in app.port_impls:
            lines.append(f"- [{pi.name}]({_slug(pi.name)}.md)")
        lines.append("")
    return "\n".join(lines)


def render_infrastructure_handlers(app: AppDoc) -> str:
    lines = ["# Handlers\n"]
    for h in app.handlers:
        lines.append(render_handler(h))
        lines.append("---\n")
    return "\n".join(lines)


def render_infrastructure_projections(app: AppDoc) -> str:
    lines = ["# Projections\n"]
    for proj in app.projections:
        lines.append(render_projection(proj))
        lines.append("---\n")
    return "\n".join(lines)


def render_infrastructure_implementations(app: AppDoc) -> str:
    lines = ["# Port Implementations\n"]
    for pi in app.port_impls:
        lines.append(render_session(pi) if hasattr(pi, "execute") else render_port(pi))
        lines.append("---\n")
    return "\n".join(lines)


def render_exceptions(app: AppDoc) -> str:
    lines = [f"# {app.name} - Exceptions\n"]
    for ex in app.exceptions:
        lines.append(render_exception(ex))
        lines.append("---\n")
    return "\n".join(lines)


def render_api_index(apps: list[AppDoc]) -> str:
    lines = ["# API Reference\n"]
    for app in apps:
        slug = _slug(app.name)
        lines.append(f"## {app.name}\n")
        lines.append(f"Version: {app.version}\n")
        if app.contexts:
            lines.append("### Domain\n")
            for ctx in app.contexts:
                lines.append(f"- [{ctx.name}](../{slug}/domain/{_slug(ctx.name)}.md)")
            lines.append("")
        if app.use_cases:
            lines.append("### Application\n")
            for uc in app.use_cases:
                lines.append(f"- [{uc.name}](../{slug}/application/{_slug(uc.name)}.md)")
            lines.append("")
        if app.handlers:
            lines.append("### Infrastructure\n")
            for h in app.handlers:
                lines.append(f"- [{h.name}](../{slug}/infrastructure/{_slug(h.name)}.md)")
            lines.append("")
        if app.exceptions:
            lines.append("### Exceptions\n")
            for ex in app.exceptions:
                desc = f" - {ex.doc}" if ex.doc else ""
                lines.append(f"- `{ex.name}`{desc}")
            lines.append("")
    return "\n".join(lines)


def render_home(apps: list[AppDoc]) -> str:
    lines = ["# API Documentation\n"]
    for app in apps:
        slug = _slug(app.name)
        lines.append(f"## {app.name}\n")
        lines.append(f"{app.description}\n")
        lines.append(f"**Version:** {app.version}\n")
        if app.repo_url:
            lines.append(f"**Repository:** {app.repo_url}\n")
        if app.contexts:
            lines.append("### Bounded Contexts\n")
            for ctx in app.contexts:
                lines.append(f"- [{ctx.name}]({slug}/domain/{_slug(ctx.name)}.md)")
            lines.append("")
        lines.append(f"- [Domain]({slug}/domain/index.md)")
        lines.append(f"- [Application]({slug}/application/index.md)")
        lines.append(f"- [Infrastructure]({slug}/infrastructure/index.md)")
        lines.append(f"- [Exceptions]({slug}/exceptions.md)")
        lines.append("- [API Reference](api/index.md)")
        lines.append("")
    return "\n".join(lines)


def render_app_home(app: AppDoc) -> str:
    lines = [f"# {app.name}\n"]
    lines.append(f"{app.description}\n")
    lines.append(f"**Version:** {app.version}\n")
    if app.repo_url:
        lines.append(f"**Repository:** {app.repo_url}\n")
    if app.contexts:
        lines.append("## Bounded Contexts\n")
        for ctx in app.contexts:
            lines.append(f"- [{ctx.name}](domain/{_slug(ctx.name)}.md)")
        lines.append("")
    lines.append("- [Domain](domain/index.md)")
    lines.append("- [Application](application/index.md)")
    lines.append("- [Infrastructure](infrastructure/index.md)")
    lines.append("- [Exceptions](exceptions.md)")
    lines.append("- [API Reference](../api/index.md)")
    lines.append("")
    return "\n".join(lines)
