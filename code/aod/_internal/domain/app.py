from __future__ import annotations

from aod._internal.core.domain_exception import DuplicateDomainTypeError
from aod._internal.domain.bounded_context import BoundedContext
from aod._internal.domain.describe import TypeDoc


class App:
    def __init__(
        self,
        name: str,
        *contexts: BoundedContext,
    ) -> None:
        seen: dict[type, str] = {}

        for ctx in contexts:
            ctx_label = ctx.name or repr(ctx)

            all_entity_types = set(ctx.aggregate_roots) | set(ctx.entities)
            for t in all_entity_types:
                if t in seen:
                    raise DuplicateDomainTypeError(t.__name__, "Entity", seen[t])
                seen[t] = ctx_label

            for s in ctx.services:
                if s in seen:
                    raise DuplicateDomainTypeError(s.__name__, "Service", seen[s])
                seen[s] = ctx_label

        self.name = name
        self.contexts = tuple(contexts)

    def describe(self) -> dict[str, list[TypeDoc]]:
        return {ctx.name or repr(ctx): ctx.describe() for ctx in self.contexts}
