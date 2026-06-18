from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import get_type_hints

from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases
from aod._internal.infrastructure.handlers.handlers import BaseHandler
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.schema.docs.generic_docs import MethodDoc


@dataclass
class HandlerDoc:
    name: str
    handler_type: str
    contract: str = ""
    session: str = ""
    description: str = ""
    is_async: bool = False
    handle: MethodDoc | None = None

    @classmethod
    def from_handler(cls, handler_cls: type[BaseHandler]) -> HandlerDoc:
        contract_name = ""
        handler_type = ""
        is_async = False

        for base in getattr(handler_cls, "__orig_bases__", ()):
            origin = getattr(base, "__origin__", None)
            if origin is None:
                continue
            origin_name = getattr(origin, "__name__", "")
            if origin_name in (
                "CommandHandler",
                "QueryHandler",
                "AsyncCommandHandler",
                "AsyncQueryHandler",
                "CommandPort",
                "QueryPort",
            ):
                handler_type = origin_name
                is_async = origin_name.startswith("Async")
                contract = get_generic_arg_from_orig_bases(handler_cls, origin)
                if contract is not None:
                    contract_name = contract.__name__

        session = ""
        hints = get_type_hints(handler_cls)
        session_type = hints.get("session")
        if session_type is not None:
            session = _session_name(session_type)

        handle = None
        handle_func = handler_cls.__dict__.get("handle")
        if handle_func is not None:
            handle = MethodDoc.from_method(handle_func)

        return cls(
            name=handler_cls.__name__,
            handler_type=handler_type,
            contract=contract_name,
            session=session,
            description=inspect.getdoc(handler_cls) or "",
            is_async=is_async,
            handle=handle,
        )


def _session_name(tp: object) -> str:
    origin = getattr(tp, "__origin__", None)
    if origin is not None:
        args = getattr(tp, "__args__", ())
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, (Session, AsyncSession)):
                return arg.__name__
        return ""
    if isinstance(tp, type):
        return tp.__name__
    return str(tp)
