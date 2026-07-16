from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from aod._internal.schema.docs.module_doc import ModuleDoc

if TYPE_CHECKING:
    from aod._internal.schema.app import App


@dataclass
class AppDoc:
    name: str
    modules: list[ModuleDoc]
    description: str = ""

    @classmethod
    def from_app(cls, app: App) -> AppDoc:
        return cls(
            name=app.name,
            description=app.description,
            modules=[ModuleDoc.from_module(mod) for mod in app.modules],
        )
