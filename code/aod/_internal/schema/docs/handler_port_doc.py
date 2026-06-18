from __future__ import annotations

from dataclasses import dataclass

from aod._internal.application.handler import (
    AsyncCommandPort,
    AsyncQueryPort,
    CommandPort,
    QueryPort,
)
from aod._internal.schema.docs.contract_doc import ContractDoc

_HANDLER_PORT_TYPES: frozenset[type] = frozenset(
    {
        CommandPort,
        QueryPort,
        AsyncCommandPort,
        AsyncQueryPort,
    }
)


@dataclass
class HandlerPortDoc:
    name: str
    handler_type: str
    kind: str
    is_async: bool
    contract_doc: ContractDoc | None = None

    @classmethod
    def from_handler_port(cls, field_name: str, annotation: object) -> HandlerPortDoc | None:
        origin = getattr(annotation, "__origin__", None)
        if origin is None or origin not in _HANDLER_PORT_TYPES:
            return None

        args = getattr(annotation, "__args__", ())
        contract_cls = args[0] if args and isinstance(args[0], type) else None

        is_async = origin in (AsyncCommandPort, AsyncQueryPort)
        kind = "command" if origin in (CommandPort, AsyncCommandPort) else "query"

        contract_doc = ContractDoc.from_contract(contract_cls) if contract_cls is not None else None

        return cls(
            name=field_name,
            handler_type=origin.__name__,
            kind=kind,
            is_async=is_async,
            contract_doc=contract_doc,
        )
