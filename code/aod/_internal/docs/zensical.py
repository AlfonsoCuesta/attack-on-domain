from __future__ import annotations

from .model import AppDoc


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def generate_zensical_toml(apps: list[AppDoc]) -> str:
    app = apps[0] if apps else None
    site_name = f"{app.name} Documentation" if app else "Documentation"
    nav_items: list[str] = []
    nav_items.append('    {"Home" = "index.md"},')
    for a in apps:
        slug = _slug(a.name)
        nav_items.append(f'    {{"{a.name}" = [')
        nav_items.append(f'        "{slug}/index.md",')
        nav_items.append(f'        "{slug}/domain/index.md",')
        nav_items.append(f'        "{slug}/domain/entities.md",')
        nav_items.append(f'        "{slug}/domain/value-objects.md",')
        nav_items.append(f'        "{slug}/domain/services.md",')
        nav_items.append(f'        "{slug}/domain/events.md",')
        nav_items.append(f'        "{slug}/application/index.md",')
        nav_items.append(f'        "{slug}/application/use-cases.md",')
        nav_items.append(f'        "{slug}/application/commands.md",')
        nav_items.append(f'        "{slug}/application/queries.md",')
        nav_items.append(f'        "{slug}/application/ports.md",')
        nav_items.append(f'        "{slug}/infrastructure/index.md",')
        nav_items.append(f'        "{slug}/infrastructure/handlers.md",')
        nav_items.append(f'        "{slug}/infrastructure/projections.md",')
        nav_items.append(f'        "{slug}/infrastructure/implementations.md",')
        nav_items.append(f'        "{slug}/exceptions.md",')
        nav_items.append("    ]},")
    nav_items.append('    {"API Reference" = "api/index.md"},')
    nav_str = "\n".join(nav_items)
    return f"""site_name = "{site_name}"
site_description = "DDD Documentation"

[theme]
name = "material"
variant = "classic"
palette = [
    {{scheme = "default", primary = "blue", accent = "blue", toggle = {{icon = "material/brightness-7", name = "Switch to light mode"}}}},
    {{scheme = "slate", primary = "blue", accent = "blue", toggle = {{icon = "material/brightness-4", name = "Switch to dark mode"}}}},
]
features = [
    "navigation.tabs",
    "navigation.tabs.sticky",
    "navigation.top",
    "search.suggest",
    "search.highlight",
    "content.code.copy",
]
font = {{text = "Roboto", code = "Roboto Mono"}}
language = "en"

[plugins]
search = {{}}

[markdown]
toc = {{permalink = true, title = "On this page"}}

nav = [
{nav_str}
]
"""
