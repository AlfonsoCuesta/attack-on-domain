from __future__ import annotations

import inspect
from dataclasses import dataclass, field

from aod._internal.application.cache.cache import AsyncCache, BaseCache
from aod._internal.application.cache.cache_key import CacheKey


@dataclass
class CacheDoc:
    name: str
    is_async: bool = False
    description: str = ""

    @classmethod
    def from_cache(cls, cache_cls: type[BaseCache]) -> CacheDoc:
        return cls(
            name=cache_cls.__name__,
            is_async=issubclass(cache_cls, AsyncCache),
            description=inspect.getdoc(cache_cls) or "",
        )


@dataclass
class CacheKeyDoc:
    name: str
    query_type: str = ""
    invalidating_commands: list[str] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_cache_key(cls, key_cls: type[CacheKey]) -> CacheKeyDoc:
        query_type = ""
        invalidating: list[str] = []
        try:
            qtype = key_cls.get_query_type()
            query_type = qtype.__name__
        except Exception:
            pass
        ctypes = key_cls.get_command_types()
        invalidating = sorted(t.__name__ for t in ctypes)
        return cls(
            name=getattr(key_cls, "__name__", ""),
            query_type=query_type,
            invalidating_commands=invalidating,
            description=inspect.getdoc(key_cls) or "",
        )
