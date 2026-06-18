from __future__ import annotations

from aod._internal.core.domain_exception import MissingHandlerError, MissingPortError
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
                raise MissingHandlerError(f"Contract {contract.__name__} has no handler in module")

        for port_cls in context.ports:
            if not any(issubclass(impl, port_cls) for impl in infrastructure.ports):
                raise MissingPortError(port_cls.__name__)

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
                    "AsyncCommandPort",
                    "AsyncQueryPort",
                ):
                    contract = get_generic_arg_from_orig_bases(handler_cls, origin)
                    if contract is not None:
                        mapping[contract] = handler_cls

        return mapping
