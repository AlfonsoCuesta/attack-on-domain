from __future__ import annotations

from typing import Any, ClassVar, Generic, get_args, get_origin

from aod._internal.application.cache.cache_key import CacheInvalidation, CacheKey, TOperation


class OperationCacheInvalidation(CacheInvalidation): ...


class OperationCacheKey(CacheKey, Generic[TOperation]):
    _operation_type: ClassVar[type]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._operation_type = cls._resolve_operation_type()
        cls._validate_operation_type(cls._operation_type)

    @classmethod
    def _resolve_operation_type(cls) -> type:
        for base in getattr(cls, "__orig_bases__", ()):
            origin = get_origin(base)
            if origin is OperationCacheKey:
                args = get_args(base)
                if args:
                    return args[0]
        raise TypeError(
            f"{cls.__name__} must be parameterized with an operation type, "
            "e.g. OperationCacheKey[MyUseCase]"
        )

    @classmethod
    def _validate_operation_type(cls, op_type: type) -> None:
        if not callable(getattr(op_type, "run", None)) and not callable(
            getattr(op_type, "read", None)
        ):
            raise TypeError(f"{op_type.__name__} is not a UseCase or ReadProjection")

    @classmethod
    def get_type(cls) -> type:
        return cls._operation_type
