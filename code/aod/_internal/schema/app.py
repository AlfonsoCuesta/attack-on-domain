from __future__ import annotations

from collections.abc import Iterable
from itertools import chain

from aod._internal.core.domain_exception import DuplicateDomainTypeError
from aod._internal.schema.module import Module


class App:
    def __init__(
        self,
        name: str,
        modules: Iterable[Module],
        description: str = "",
    ) -> None:
        modules = list(modules)
        self._validate(modules)

        self.name = name
        self.description = description
        self.modules = tuple(modules)

    @staticmethod
    def _validate(modules: list[Module]) -> None:
        seen: dict[type, tuple[str, str]] = {}

        for mod in modules:
            ctx = mod.context

            for t in chain(ctx.aggregate_roots, ctx.entities):
                if t in seen:
                    prev_mod, prev_role = seen[t]
                    raise DuplicateDomainTypeError(t.__name__, prev_role, prev_mod)
                seen[t] = (mod.name, "Entity")

            for s in ctx.services:
                if s in seen:
                    prev_mod, prev_role = seen[s]
                    raise DuplicateDomainTypeError(s.__name__, prev_role, prev_mod)
                seen[s] = (mod.name, "Service")

            for uc in ctx.use_cases:
                if uc in seen:
                    prev_mod, prev_role = seen[uc]
                    raise DuplicateDomainTypeError(uc.__name__, prev_role, prev_mod)
                seen[uc] = (mod.name, "UseCase")

            for c in ctx.contracts:
                if c in seen:
                    prev_mod, prev_role = seen[c]
                    raise DuplicateDomainTypeError(c.__name__, prev_role, prev_mod)
                seen[c] = (mod.name, "Contract")

            for h in mod.infrastructure.handlers:
                if h in seen:
                    prev_mod, prev_role = seen[h]
                    raise DuplicateDomainTypeError(h.__name__, prev_role, prev_mod)
                seen[h] = (mod.name, "Handler")
