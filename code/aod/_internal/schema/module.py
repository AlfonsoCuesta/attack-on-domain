from __future__ import annotations

from aod._internal.application.handler import CommandPort, QueryPort
from aod._internal.core.domain_exception import InvalidCommandFieldTypeError
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases
from aod._internal.schema.bounded_context import BoundedContext
from aod._internal.schema.infrastructure import HandlerType, Infrastructure


class Module:
    def __init__(
        self,
        name: str,
        context: BoundedContext,
        infrastructure: Infrastructure,
    ):
        self._validate(context, infrastructure)

        self.name = name
        self.context = context
        self.infrastructure = infrastructure

    @staticmethod
    def _validate(context: BoundedContext, infrastructure: Infrastructure) -> None:
        handler_contracts: dict[type, HandlerType] = Module._map_handler_contracts(
            infrastructure.handlers
        )

        for contract in context.contracts:
            if contract not in handler_contracts:
                raise InvalidCommandFieldTypeError(
                    f"Contract {contract.__name__} has no handler in module"
                )

        for port in context.ports:
            origin = getattr(port, "__origin__", None)
            if origin is not None and issubclass(origin, (CommandPort, QueryPort)):
                args = getattr(port, "__args__", ())
                if args and args[0] not in handler_contracts:
                    raise InvalidCommandFieldTypeError(
                        f"Port {origin.__name__}[{args[0].__name__}] has no handler in module"
                    )

    @staticmethod
    def _map_handler_contracts(
        handlers: tuple[HandlerType, ...],
    ) -> dict[type, HandlerType]:
        mapping: dict[type, HandlerType] = {}

        for handler_cls in handlers:
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
                    contract = get_generic_arg_from_orig_bases(handler_cls, origin)
                    if contract is not None:
                        mapping[contract] = handler_cls

        return mapping
