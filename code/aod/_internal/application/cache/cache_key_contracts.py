from __future__ import annotations

from typing import Any, ClassVar, Generic, get_args, get_origin

from aod._internal.application.cache.cache_key import CacheInvalidation, CacheKey, TQuery_co
from aod._internal.application.contracts import Command, Query


class ContractCacheInvalidation(CacheInvalidation):
    target_type: type[Command]


class ContractCacheKey(CacheKey, Generic[TQuery_co]):
    _query_type: ClassVar[type[Query]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._query_type = cls._resolve_query_type()

    @classmethod
    def _resolve_query_type(cls) -> type[Query]:
        for base in getattr(cls, "__orig_bases__", ()):
            origin = get_origin(base)
            if origin is ContractCacheKey:
                args = get_args(base)
                if args:
                    tp = args[0]
                    if isinstance(tp, type) and issubclass(tp, Query):
                        return tp
        raise TypeError(
            f"{cls.__name__} must be parameterized with a Query type, "
            "e.g. ContractCacheKey[GetUser]"
        )

    @classmethod
    def get_type(cls) -> type[Query]:
        return cls._query_type

    def get_command_types(self) -> set[type[Command]]:
        return {
            inv.target_type
            for inv in self.invalidate()
            if isinstance(inv, ContractCacheInvalidation)
        }
