__all__ = [
    "BaseGuardedTypeHandler",
    "get_generic_arg_from_mro",
    "get_generic_arg_from_orig_bases",
    "ServiceTypeHandler",
    "validate_generic_arg_is_subclass",
]


def __getattr__(name: str) -> object:
    if name in __all__:
        if name in ("BaseGuardedTypeHandler",):
            import aod._internal.core.type_handlers.base_guarded_handler as _m

            return getattr(_m, name)
        if name in ("ServiceTypeHandler",):
            import aod._internal.core.type_handlers.service_handler as _m

            return getattr(_m, name)
        if name in ("get_generic_arg_from_mro", "get_generic_arg_from_orig_bases", "validate_generic_arg_is_subclass"):
            import aod._internal.core.type_handlers.generic_utils as _m

            return getattr(_m, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
