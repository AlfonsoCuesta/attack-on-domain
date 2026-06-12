from __future__ import annotations

from .model import AppDoc


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def generate_zensical_toml(apps: list[AppDoc]) -> str:
    lines: list[str] = []
    lines.append("[site]")
    if apps:
        lines.append(f'name = "{apps[0].name} Documentation"')
    else:
        lines.append('name = "Documentation"')
    lines.append('site_url = ""')
    lines.append("")
    lines.append("[nav]")
    lines.append('"Home" = "index.md"')
    lines.append('"Getting Started" = "getting-started/"')
    lines.append('"Domain" = "domain/"')
    lines.append('"Application" = "application/"')
    lines.append('"Infrastructure" = "infrastructure/"')
    lines.append('"Exceptions" = "exceptions.md"')
    lines.append('"API Reference" = "api/"')
    lines.append("")
    lines.append("[theme]")
    lines.append('name = "material"')
    lines.append('variant = "classic"')
    lines.append('palette = [{ scheme = "default", primary = "indigo", accent = "indigo", toggle = { icon = "material/brightness-7", name = "Switch to dark mode" } }, { scheme = "slate", primary = "indigo", accent = "indigo", toggle = { icon = "material/brightness-4", name = "Switch to light mode" } }]')
    lines.append('features = ["navigation.tabs", "navigation.tabs.sticky", "navigation.indexes"]')
    lines.append("")
    lines.append("[markdown_extensions]")
    lines.append("pymdownx.highlight = { anchor_linenums = true }")
    lines.append("pymdownx.superfences = {}")
    lines.append("pymdownx.tabbed = { alternate_style = true }")
    lines.append("")
    lines.append("[plugins]")
    lines.append("search = {}")
    return "\n".join(lines)
