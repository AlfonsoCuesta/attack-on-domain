from __future__ import annotations

from typing import get_args, get_origin

from aod._internal.core.domain_exception import DomainException


def get_last_generic_arg(cls: type) -> type | None:
    for base in getattr(cls, "__orig_bases__", ()):
        origin = get_origin(base)
        if origin is not None:
            args = get_args(base)
            if args:
                return args[-1]
    return None


def get_generic_arg_from_orig_bases(cls: type, target_origin: type, index: int = 0) -> type | None:
    for base in getattr(cls, "__orig_bases__", ()):
        origin = get_origin(base)
        if origin is target_origin:
            args = get_args(base)
            if len(args) > index:
                return args[index]
    return None


def get_generic_arg_from_mro(cls: type, target_origins: tuple[type, ...]) -> type | None:
    for base in cls.__mro__:
        for orig_base in getattr(base, "__orig_bases__", []):
            origin = get_origin(orig_base)
            if origin in target_origins:
                args = get_args(orig_base)
                if args:
                    return args[0]
    return None


def validate_generic_arg_is_subclass(
    cls: type,
    target_origin: type,
    expected_base: type,
    *,
    arg_name: str = "Generic parameter",
) -> None:
    t = get_generic_arg_from_orig_bases(cls, target_origin)
    if isinstance(t, type) and not issubclass(t, expected_base):
        msg = f"{arg_name} for {cls.__name__} must be a {expected_base.__name__} subclass, got {t.__name__}"
        raise DomainException(msg)


def validate_handler_subclass(
    cls: type,
    handler_class: type,
    expected_base: type,
    *,
    arg_name: str = "Generic parameter",
) -> None:
    for orig_base in getattr(cls, "__orig_bases__", ()):
        origin = get_origin(orig_base)
        if origin is not None and isinstance(origin, type) and issubclass(origin, handler_class):
            validate_generic_arg_is_subclass(
                cls,
                origin,
                expected_base,
                arg_name=arg_name,
            )
            break
