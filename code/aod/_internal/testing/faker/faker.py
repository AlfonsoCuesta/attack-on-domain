from __future__ import annotations

from functools import lru_cache
from typing import Any, Generic, TypeVar, Union, cast, get_args, get_origin

from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.value_object import ValueObject
from aod._internal.testing.helpers import build
from polyfactory.factories.pydantic_factory import ModelFactory as PolyModelFactory
from pydantic import create_model

T = TypeVar("T")

_DOMAIN_BASES: tuple[type, ...] = (RootEntity, Entity, ValueObject)
DomainType = RootEntity | Entity | ValueObject
DT = TypeVar("DT", bound=DomainType)

__all__ = [
    "DomainType",
    "FakeDomain",
]


def _flatten(tp: Any) -> type:
    if isinstance(tp, type) and issubclass(tp, _DOMAIN_BASES):
        return cast(type, tp.__raw_model__)
    origin = get_origin(tp)
    if origin is not None:
        args = get_args(tp)
        non_none = tuple(a for a in args if a is not type(None))
        if len(non_none) < len(args):
            if len(non_none) == 1:
                return _flatten(non_none[0])
            return cast(type, Union[tuple(_flatten(a) for a in non_none)])
        return cast(type, origin[tuple(_flatten(a) for a in args)])
    return cast(type, tp)


def _to_domain(tp: type, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(tp, type) and issubclass(tp, _DOMAIN_BASES):
        raw_model = cast(type, cast(Any, tp).__raw_model__)
        if isinstance(value, raw_model):
            return build(tp, **value.model_dump())
        return value
    origin = get_origin(tp)
    if origin is not None:
        args = get_args(tp)
        if origin is list and args:
            return [_to_domain(args[0], v) for v in value]
        if origin is dict and args:
            return {k: _to_domain(args[1], v) for k, v in value.items()}
        if origin is set and args:
            return {_to_domain(args[0], v) for v in value}
        if origin is tuple and args:
            return tuple(_to_domain(args[i], v) for i, v in enumerate(value))
    return value


@lru_cache(maxsize=256)
def _factory_for(cls: type[DomainType]) -> type[PolyModelFactory]:
    field_defs: dict[str, Any] = {}
    for name, field_info in cls.__model_fields__.items():
        field_defs[name] = (_flatten(field_info.annotation), ...)
    flat = create_model(f"{cls.__name__}Flat", **field_defs)
    return cast(type[PolyModelFactory], PolyModelFactory.create_factory(flat))


class FakeDomain(Generic[T]):
    def __init__(self, model_cls: type[T], **defaults: Any) -> None:
        if not (isinstance(model_cls, type) and issubclass(model_cls, _DOMAIN_BASES)):
            raise TypeError(
                f"Expected an Entity, RootEntity, or ValueObject subclass, got {model_cls}"
            )
        self._model: type[DomainType] = cast(type[DomainType], model_cls)
        self._defaults = defaults

    def __call__(self, **overrides: Any) -> T:
        merged = {**self._defaults, **overrides}
        missing = [n for n in self._model.__model_fields__ if n not in merged]

        if missing:
            poly = _factory_for(self._model)
            flat = poly.build()
            for n in missing:
                fi = self._model.__model_fields__[n]
                merged[n] = _to_domain(fi.annotation, getattr(flat, n))

        return cast(T, self._model.reconstruct(**merged))

    def batch(self, count: int, overrides_list: list[dict[str, Any]] | None = None) -> list[T]:
        if overrides_list is not None:
            return [self(**o) for o in overrides_list]
        return [self() for _ in range(count)]
