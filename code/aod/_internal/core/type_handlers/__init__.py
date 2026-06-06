from __future__ import annotations

from typing import TYPE_CHECKING

# Runtime: lazy imports via __getattr__ to avoid circular dependencies
# Type checker: explicit imports in TYPE_CHECKING for static resolution

if TYPE_CHECKING:
    from .base_guarded_handler import BaseGuardedTypeHandler
    from .service_handler import ServiceTypeHandler
    from .generic_utils import (
        get_generic_arg_from_mro,
        get_generic_arg_from_orig_bases,
        get_last_generic_arg,
        validate_generic_arg_is_subclass,
        validate_handler_subclass,
    )

__all__ = [
    "BaseGuardedTypeHandler",
    "get_generic_arg_from_mro",
    "get_generic_arg_from_orig_bases",
    "get_last_generic_arg",
    "ServiceTypeHandler",
    "validate_generic_arg_is_subclass",
    "validate_handler_subclass",
]


def __getattr__(name: str) -> object:
    if name in __all__:
        if name in ("BaseGuardedTypeHandler",):
            import aod._internal.core.type_handlers.base_guarded_handler as _m

            return getattr(_m, name)
        if name in ("ServiceTypeHandler",):
            import aod._internal.core.type_handlers.service_handler as _m

            return getattr(_m, name)
        if name in (
            "get_generic_arg_from_mro",
            "get_generic_arg_from_orig_bases",
            "get_last_generic_arg",
            "validate_generic_arg_is_subclass",
            "validate_handler_subclass",
        ):
            import aod._internal.core.type_handlers.generic_utils as _m

            return getattr(_m, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
