from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, ClassVar, Generic, TypeVar, get_type_hints

from aod._internal.application.contracts import Command, Query

TQuery_co = TypeVar("TQuery_co", bound=Query, covariant=True)


@dataclass(frozen=True, slots=True)
class Invalidation:
    command_type: type[Command]
    key_fn: Callable[[Any], str]


class CacheKey(ABC, Generic[TQuery_co]):
    _query_type: ClassVar[type[Query]]
    _command_types: ClassVar[set[type[Command]]] = set()
    _invalidation_map: ClassVar[dict[type[Command], Callable[[Any], str]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        key_method = cls.__dict__.get("key")
        if key_method is not None and not getattr(key_method, "__isabstractmethod__", False):
            cls._extract_and_store_query_type(cls)
        invalidate_method = cls.__dict__.get("invalidate")
        if invalidate_method is not None and not getattr(
            invalidate_method, "__isabstractmethod__", False
        ):
            cls._extract_and_store_invalidation_info(cls)

    @classmethod
    def _extract_and_store_query_type(cls, target_cls: type) -> None:
        hints = get_type_hints(target_cls.key)
        for name, tp in hints.items():
            if name in ("self", "return"):
                continue
            if isinstance(tp, type) and issubclass(tp, Query):
                target_cls._query_type = tp
                return
        raise TypeError(
            f"Could not determine Query type for {target_cls.__name__}. "
            "Ensure the key() method has a type hint for its first parameter."
        )

    @classmethod
    def _extract_and_store_invalidation_info(cls, target_cls: type) -> None:
        instance = target_cls()
        invs: list[Invalidation] = instance.invalidate()
        target_cls._invalidation_map = {}
        target_cls._command_types = set()
        for inv in invs:
            target_cls._invalidation_map[inv.command_type] = inv.key_fn
            target_cls._command_types.add(inv.command_type)

    @abstractmethod
    def key(self, query: TQuery_co) -> str: ...

    @abstractmethod
    def invalidate(self) -> list[Invalidation]: ...

    @classmethod
    def get_query_type(cls) -> type[Query]:
        return cls._query_type

    @classmethod
    def get_command_types(cls) -> set[type[Command]]:
        return cls._command_types

    @classmethod
    def get_invalidation_key_fn(cls, command_type: type[Command]) -> Callable[[Any], str] | None:
        return cls._invalidation_map.get(command_type)
