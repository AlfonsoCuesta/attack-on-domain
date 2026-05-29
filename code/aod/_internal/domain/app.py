from __future__ import annotations

from aod._internal.domain.bounded_context import BoundedContext


class App:
    def __init__(
        self,
        name: str,
        *contexts: BoundedContext,
    ) -> None:
        self.name = name
        self.contexts = tuple(contexts)
