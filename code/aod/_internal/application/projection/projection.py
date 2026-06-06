from __future__ import annotations

from types import UnionType
from typing import Generic, TypeVar, get_args, get_origin

from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases

class ReadModel(BaseSealed):
    pass


TReadModel = TypeVar("TReadModel", bound=ReadModel | None)


def _flatten_union(tp: object) -> list[type]:
    origin = get_origin(tp)
    if origin is UnionType or origin is type(UnionType):
        return [a for arg in get_args(tp) for a in _flatten_union(arg)]
    if isinstance(tp, type):
        return [tp]
    return []


def _validate_projection_arg(cls: type) -> None:
    tp = get_generic_arg_from_orig_bases(cls, BaseProjection, index=0)
    if tp is None or isinstance(tp, TypeVar):
        return

    for t in _flatten_union(tp):
        if t is not type(None) and not issubclass(t, ReadModel):
            raise DomainException(
                f"Projection type must be a ReadModel subclass or None, "
                f"got {t.__name__}"
            )


class BaseProjection(BaseSealed, Generic[TReadModel]):
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        _validate_projection_arg(cls)


class ProjectionQuery(BaseProjection, Generic[TReadModel]):
    pass


class ProjectionCommand(BaseProjection, Generic[TReadModel]):
    pass
