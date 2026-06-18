from __future__ import annotations

from pathlib import Path
from typing import Any

from aod._internal.schema.app import App
from aod._internal.schema.docs.bounded_context_doc import BoundedContextDoc
from aod._internal.schema.docs.generic_docs import FieldDoc, MethodDoc, ParamDoc
from aod._internal.schema.docs.module_doc import ModuleDoc


class AutoDoc:
    def __init__(
        self,
        app: App,
        output_dir: str | Path,
        *,
        site_name: str = "",
        site_description: str = "",
        repo_url: str = "",
        repo_name: str = "",
        edit_uri: str = "edit/main/docs/",
    ) -> None:
        self.app = app
        self.output_dir = Path(output_dir)
        self.modules = [ModuleDoc.from_module(mod) for mod in app.modules]
        self.site_name = site_name or app.name
        self.site_description = site_description or app.description
        self.repo_url = repo_url
        self.repo_name = repo_name or app.name
        self.edit_uri = edit_uri

    def generate(self) -> Path:
        root = self.output_dir
        docs = root / "docs"

        self._write(root / "zensical.toml", self._render_zensical_toml())
        self._write(docs / "index.md", self._render_home())

        for mod in self.modules:
            slug = self._slug(mod.name)
            bc_dir = docs / "bounded-contexts" / slug
            self._write(bc_dir / "index.md", self._render_bc_page(mod))
            self._write(bc_dir / "glossary.md", self._render_glossary(mod))
            self._write(bc_dir / "entities.md", self._render_entities(mod))
            self._write(bc_dir / "infrastructure.md", self._render_infrastructure(mod))

        self._copy_default_asset(docs / "stylesheets", "extra.css", "styles/extra.css")
        self._copy_default_asset(docs / "overrides", "main.html", "overrides/main.html")

        return root

    # ---- helpers ----

    @staticmethod
    def _slug(name: str) -> str:
        return name.lower().replace(" ", "-").replace("_", "-")

    @staticmethod
    def _write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _copy_default_asset(self, dst_dir: Path, dst_name: str, src_rel: str) -> None:
        dst = dst_dir / dst_name
        if dst.exists():
            return
        src = Path(__file__).parent / src_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    # ---- zensical config ----

    def _render_zensical_toml(self) -> str:
        nav_items: list[Any] = [{"Home": "index.md"}]

        for mod in self.modules:
            slug = self._slug(mod.name)
            label = mod.domain.name or mod.name
            nav_items.append(
                {
                    label: [
                        f"bounded-contexts/{slug}/index.md",
                        {"Glossary": f"bounded-contexts/{slug}/glossary.md"},
                        {"Entities": f"bounded-contexts/{slug}/entities.md"},
                        {"Infrastructure": f"bounded-contexts/{slug}/infrastructure.md"},
                    ]
                }
            )

        nav = self._format_nav(nav_items)

        repo_url_line = f'repo_url = "{self.repo_url}"\n' if self.repo_url else ""
        repo_name_line = f'repo_name = "{self.repo_name}"\n' if self.repo_name else ""

        return "\n".join(
            [
                f'site_name = "{self.site_name}"',
                'site_url = ""',
                f'site_description = "{self.site_description}"',
                f"{repo_url_line}{repo_name_line}".rstrip(),
                f'edit_uri = "{self.edit_uri}"',
                'extra_css = ["stylesheets/extra.css"]',
                "",
                "nav = " + nav,
                "",
                "[theme]",
                'name = "material"',
                'variant = "classic"',
                "palette = [",
                '    {scheme = "default", primary = "blue", accent = "blue", toggle = {icon = "material/brightness-7", name = "Switch to light mode"}},',
                '    {scheme = "slate", primary = "blue", accent = "blue", toggle = {icon = "material/brightness-4", name = "Switch to dark mode"}},',
                "]",
                "features = [",
                '    "navigation.tabs",',
                '    "navigation.tabs.sticky",',
                '    "navigation.indexes",',
                '    "navigation.top",',
                '    "search.suggest",',
                '    "search.highlight",',
                '    "content.code.copy",',
                '    "content.tabs.link",',
                "]",
                'font = {text = "Roboto", code = "Roboto Mono"}',
                'custom_dir = "docs/overrides"',
                'icon = {repo = "fontawesome/brands/github"}',
                'language = "en"',
                "",
                "[plugins]",
                "search = {}",
                "",
                "[markdown]",
                'toc = {permalink = true, title = "On this page"}',
                "",
            ]
        )

    def _format_nav(self, items: list[Any], indent: str = "") -> str:
        parts = ["["]
        for i, item in enumerate(items):
            comma = "," if i < len(items) - 1 else ""
            if isinstance(item, str):
                parts.append(f'\n{indent}    "{item}"{comma}')
            elif isinstance(item, dict):
                for key, value in item.items():
                    if isinstance(value, list):
                        inner = self._format_nav(value, indent + "    ")
                        parts.append(f'\n{indent}    {{ "{key}" = {inner} }}{comma}')
                    else:
                        parts.append(f'\n{indent}    {{ "{key}" = "{value}" }}{comma}')
        parts.append(f"\n{indent}]")
        return "".join(parts)

    # ---- Home page ----

    @staticmethod
    def _label(mod: ModuleDoc) -> str:
        return mod.domain.name or mod.name

    def _render_home(self) -> str:
        lines: list[str] = [
            "---",
            "hide:",
            "  - navigation",
            "  - toc",
            "---",
            "",
            '<div class="home-hero">',
            f"  <h1>{self.site_name}</h1>",
        ]
        if self.site_description:
            lines.append(f'  <p class="description">{self.site_description}</p>')
        lines.append("</div>")

        if self.modules:
            lines.extend(
                [
                    "",
                    '<div class="home-features">',
                ]
            )
            for mod in self.modules:
                slug = self._slug(mod.name)
                label = self._label(mod)
                desc = self._bc_description(mod.domain)
                lines.extend(
                    [
                        '  <div class="feature-card">',
                        f'    <h3><a href="bounded-contexts/{slug}/">{label}</a></h3>',
                        f"    <p>{desc}</p>",
                        "  </div>",
                    ]
                )
            lines.append("</div>")

        lines.append("")
        return "\n".join(lines)

    # ---- BoundedContext page ----

    def _render_bc_page(self, mod: ModuleDoc) -> str:
        domain = mod.domain
        lines: list[str] = [
            "---",
            "hide:",
            "  - navigation",
            "  - toc",
            "---",
            "",
            f"# {self._label(mod)}",
        ]

        desc = self._bc_description(domain)
        if desc:
            lines.extend(["", desc])

        lines.extend(["", '<div class="home-features">'])

        lines.extend(
            [
                '  <div class="feature-card">',
                '    <h3><a href="glossary/">Glossary</a></h3>',
                "    <p>Domain terms, entities, value objects, and services</p>",
                "  </div>",
                '  <div class="feature-card">',
                '    <h3><a href="entities/">Domain Entities</a></h3>',
                "    <p>Root entities, entities, value objects, and services</p>",
                "  </div>",
                '  <div class="feature-card">',
                '    <h3><a href="infrastructure/">Infrastructure</a></h3>',
                "    <p>Handlers, sessions, ports, and projections</p>",
                "  </div>",
            ]
        )
        lines.append("</div>")

        # Use Cases
        if domain.use_cases:
            lines.extend(["", "## Use Cases", ""])
            for uc in domain.use_cases:
                lines.append(f"### {uc.name}")
                if uc.description:
                    lines.extend(["", uc.description])
                if uc.handler_ports:
                    lines.extend(["", "**Ports:**", ""])
                    for hp in uc.handler_ports:
                        lines.append(
                            f"- `{hp.name}`: `{hp.handler_type}[{hp.contract_doc.name if hp.contract_doc else ''}]`"
                        )
                if uc.params:
                    lines.extend(["", "**Parameters:**", ""])
                    lines.append(self._render_param_table(uc.params))
                lines.append("")

        # Projections
        if mod.infrastructure.projections:
            lines.extend(["", "## Projections", ""])
            for proj in mod.infrastructure.projections:
                lines.append(f"### {proj.name}")
                if proj.description:
                    lines.extend(["", proj.description])
                if proj.projection_type:
                    lines.extend(["", f"**Type:** `{proj.projection_type}`"])
                if proj.session:
                    lines.extend(["", f"**Session:** `{proj.session}`"])
                if proj.ports:
                    lines.extend(["", "**Ports:**", ""])
                    for p in proj.ports:
                        lines.append(f"- `{p.name}`: `{p.type_name}`")
                lines.append("")

        lines.append("")
        return "\n".join(lines)

    # ---- Glossary ----

    def _render_glossary(self, mod: ModuleDoc) -> str:
        domain = mod.domain
        lines: list[str] = [
            "---",
            "hide:",
            "  - navigation",
            "  - toc",
            "---",
            "",
            f"# {self._label(mod)} — Glossary",
            "",
        ]

        if domain.roots:
            lines.append("## Root Entities")
            lines.append("")
            for root in domain.roots:
                lines.append(f"- **{root.name}**")
                if root.description:
                    lines.append(f"  - {root.description}")
            lines.append("")

        if domain.entities:
            lines.append("## Entities")
            lines.append("")
            for ent in domain.entities:
                lines.append(f"- **{ent.name}**")
                if ent.description:
                    lines.append(f"  - {ent.description}")
            lines.append("")

        if domain.value_objects:
            lines.append("## Value Objects")
            lines.append("")
            for vo in domain.value_objects:
                lines.append(f"- **{vo.name}**")
                if vo.description:
                    lines.append(f"  - {vo.description}")
            lines.append("")

        if domain.services:
            lines.append("## Services")
            lines.append("")
            for svc in domain.services:
                lines.append(f"- **{svc.name}**")
                if svc.description:
                    lines.append(f"  - {svc.description}")
            lines.append("")

        if (
            not domain.roots
            and not domain.entities
            and not domain.value_objects
            and not domain.services
        ):
            lines.append("_No domain types defined._")
            lines.append("")

        lines.append("")
        return "\n".join(lines)

    # ---- Entities detail ----

    def _render_entities(self, mod: ModuleDoc) -> str:
        domain = mod.domain
        lines: list[str] = [
            "---",
            "hide:",
            "  - navigation",
            "  - toc",
            "---",
            "",
            f"# {self._label(mod)} — Domain Entities",
            "",
        ]

        if domain.roots:
            for root in domain.roots:
                lines.append(f"## {root.name}")
                if root.description:
                    lines.extend(["", root.description])
                if root.fields:
                    lines.extend(["", "**Fields:**", ""])
                    lines.append(self._render_field_table(root.fields))
                if root.methods:
                    lines.extend(["", "**Methods:**", ""])
                    for m in root.methods:
                        lines.append(self._render_method_block(m))
                if root.commands:
                    lines.append("")
                    lines.append(f"**Commands:** {', '.join(f'`{c}`' for c in root.commands)}")
                if root.queries:
                    lines.append("")
                    lines.append(f"**Queries:** {', '.join(f'`{q}`' for q in root.queries)}")
                lines.append("")

        if domain.entities:
            for ent in domain.entities:
                lines.append(f"## {ent.name}")
                if ent.description:
                    lines.extend(["", ent.description])
                if ent.fields:
                    lines.extend(["", "**Fields:**", ""])
                    lines.append(self._render_field_table(ent.fields))
                if ent.methods:
                    lines.extend(["", "**Methods:**", ""])
                    for m in ent.methods:
                        lines.append(self._render_method_block(m))
                lines.append("")

        if domain.value_objects:
            for vo in domain.value_objects:
                lines.append(f"## {vo.name}")
                if vo.description:
                    lines.extend(["", vo.description])
                if vo.fields:
                    lines.extend(["", "**Fields:**", ""])
                    lines.append(self._render_field_table(vo.fields))
                if vo.methods:
                    lines.extend(["", "**Methods:**", ""])
                    for m in vo.methods:
                        lines.append(self._render_method_block(m))
                lines.append("")

        if domain.services:
            for svc in domain.services:
                lines.append(f"## {svc.name}")
                if svc.description:
                    lines.extend(["", svc.description])
                if svc.methods:
                    lines.extend(["", "**Methods:**", ""])
                    for m in svc.methods:
                        lines.append(self._render_method_block(m))
                lines.append("")

        if (
            not domain.roots
            and not domain.entities
            and not domain.value_objects
            and not domain.services
        ):
            lines.append("_No domain entities defined._")
            lines.append("")

        lines.append("")
        return "\n".join(lines)

    # ---- Infrastructure detail ----

    def _render_infrastructure(self, mod: ModuleDoc) -> str:
        infra = mod.infrastructure
        lines: list[str] = [
            "---",
            "hide:",
            "  - navigation",
            "  - toc",
            "---",
            "",
            f"# {self._label(mod)} — Infrastructure",
            "",
        ]

        if infra.handlers:
            lines.append("## Handlers")
            lines.append("")
            for h in infra.handlers:
                lines.append(f"### {h.name}")
                if h.description:
                    lines.extend(["", h.description])
                lines.extend(["", f"- **Type:** `{h.handler_type}`"])
                if h.contract:
                    lines.append(f"- **Contract:** `{h.contract}`")
                if h.session:
                    lines.append(f"- **Session:** `{h.session}`")
                if h.is_async:
                    lines.append("- **Async:** Yes")
                if h.handle:
                    lines.extend(["", "**Handle method:**", ""])
                    lines.append(self._render_method_block(h.handle))
                lines.append("")

        if infra.sessions:
            lines.append("## Sessions")
            lines.append("")
            for s in infra.sessions:
                lines.append(f"### {s.name}")
                if s.description:
                    lines.extend(["", s.description])
                if s.is_async:
                    lines.append("- **Async:** Yes")
                lines.append("")

        if infra.ports:
            lines.append("## Ports")
            lines.append("")
            for p in infra.ports:
                lines.append(f"### {p.name}")
                lines.extend(["", f"- **Type:** `{p.type_name}`"])
                if p.description:
                    lines.extend(["", p.description])
                if p.is_async:
                    lines.append("- **Async:** Yes")
                if p.fields:
                    lines.extend(["", "**Fields:**", ""])
                    lines.append(self._render_field_table(p.fields))
                if p.methods:
                    lines.extend(["", "**Methods:**", ""])
                    for m in p.methods:
                        lines.append(self._render_method_block(m))
                lines.append("")

        if infra.projections:
            lines.append("## Projections")
            lines.append("")
            for proj in infra.projections:
                lines.append(f"### {proj.name}")
                if proj.description:
                    lines.extend(["", proj.description])
                lines.extend(["", f"- **Type:** `{proj.projection_type}`"])
                if proj.session:
                    lines.append(f"- **Session:** `{proj.session}`")
                if proj.is_async:
                    lines.append("- **Async:** Yes")
                if proj.ports:
                    lines.extend(["", "**Ports:**", ""])
                    for p in proj.ports:
                        lines.append(f"- `{p.name}`: `{p.type_name}`")
                if proj.read:
                    lines.extend(["", "**Read method:**", ""])
                    lines.append(self._render_method_block(proj.read))
                if proj.write:
                    lines.extend(["", "**Write method:**", ""])
                    lines.append(self._render_method_block(proj.write))
                lines.append("")

        if not infra.handlers and not infra.sessions and not infra.ports and not infra.projections:
            lines.append("_No infrastructure defined._")
            lines.append("")

        lines.append("")
        return "\n".join(lines)

    # ---- shared renderers ----

    @staticmethod
    def _bc_description(domain: BoundedContextDoc) -> str:
        parts: list[str] = []
        if domain.roots:
            parts.append(
                f"{len(domain.roots)} root entit{'y' if len(domain.roots) == 1 else 'ies'}"
            )
        if domain.entities:
            parts.append(
                f"{len(domain.entities)} entit{'y' if len(domain.entities) == 1 else 'ies'}"
            )
        if domain.value_objects:
            parts.append(
                f"{len(domain.value_objects)} value object{'s' if len(domain.value_objects) != 1 else ''}"
            )
        if domain.services:
            parts.append(
                f"{len(domain.services)} service{'s' if len(domain.services) != 1 else ''}"
            )
        if domain.use_cases:
            parts.append(
                f"{len(domain.use_cases)} use case{'s' if len(domain.use_cases) != 1 else ''}"
            )
        return ", ".join(parts) if parts else "No domain types defined"

    @staticmethod
    def _render_field_table(fields: list[FieldDoc]) -> str:
        if not fields:
            return ""
        lines = [
            '<table class="param-table">',
            "<tr><th>Name</th><th>Type</th><th>Default</th><th>Description</th></tr>",
        ]
        for f in fields:
            lines.append(
                f"<tr><td>{f.name}</td><td><code>{f.type_name}</code></td><td>{f.default}</td><td>{f.description}</td></tr>"
            )
        lines.append("</table>")
        return "\n".join(lines)

    @staticmethod
    def _render_param_table(params: list[ParamDoc]) -> str:
        if not params:
            return ""
        lines = [
            '<table class="param-table">',
            "<tr><th>Name</th><th>Type</th><th>Default</th><th>Description</th></tr>",
        ]
        for p in params:
            lines.append(
                f"<tr><td>{p.name}</td><td><code>{p.type_name}</code></td><td>{p.default}</td><td>{p.description}</td></tr>"
            )
        lines.append("</table>")
        return "\n".join(lines)

    @staticmethod
    def _render_method_block(m: MethodDoc) -> str:
        def esc(t: str) -> str:
            return t.replace("[", "\\[").replace("]", "\\]")

        params_str = (
            ", ".join(f"{p.name}: {esc(p.type_name)}" for p in m.params) if m.params else ""
        )
        lines = [
            f'<div class="signature"><span class="keyword">def</span> <span class="param">{m.name}</span>({params_str})'
        ]
        if m.return_type:
            lines[0] += (
                f' <span class="arrow">-&gt;</span> <span class="type">{esc(m.return_type)}</span>'
            )
        lines[0] += "</div>"
        if m.description:
            lines.append(f"\n{m.description}")
        return "\n".join(lines)
