from __future__ import annotations

from typing import TYPE_CHECKING

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
    "ServiceTypeHandler",
    "get_generic_arg_from_mro",
    "get_generic_arg_from_orig_bases",
    "get_last_generic_arg",
    "validate_generic_arg_is_subclass",
    "validate_handler_subclass",
]

_LAZY_IMPORTS: dict[str, str] = {
    "BaseGuardedTypeHandler": "aod._internal.core.type_handlers.base_guarded_handler",
    "ServiceTypeHandler": "aod._internal.core.type_handlers.service_handler",
    "get_generic_arg_from_mro": "aod._internal.core.type_handlers.generic_utils",
    "get_generic_arg_from_orig_bases": "aod._internal.core.type_handlers.generic_utils",
    "get_last_generic_arg": "aod._internal.core.type_handlers.generic_utils",
    "validate_generic_arg_is_subclass": "aod._internal.core.type_handlers.generic_utils",
    "validate_handler_subclass": "aod._internal.core.type_handlers.generic_utils",
}


def __getattr__(name: str) -> object:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        return getattr(module, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
