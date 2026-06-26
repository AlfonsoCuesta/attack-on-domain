import re
from typing import Any, Callable, overload

import annotated_types
from pydantic import Field as PField
from pydantic import PrivateAttr


class Unset:
    def __repr__(self) -> str:
        return "UNSET FIELD"


_IDENTITY_MARKER = object()


@overload
def Field(
    default: Any,
    *,
    id: bool = ...,
    default_factory: Callable[[], Any] | None = ...,
    gt: annotated_types.SupportsGt | None = ...,
    ge: annotated_types.SupportsGe | None = ...,
    lt: annotated_types.SupportsLt | None = ...,
    le: annotated_types.SupportsLe | None = ...,
    multiple_of: float | None = ...,
    strict: bool | None = ...,
    min_length: int | None = ...,
    max_length: int | None = ...,
    pattern: str | re.Pattern[str] | None = ...,
    allow_inf_nan: bool | None = ...,
    max_digits: int | None = ...,
    decimal_places: int | None = ...,
    description: str | None = ...,
    init: bool = True,
) -> Any: ...


@overload
def Field(
    *,
    default_factory: Callable[[], Any],
    id: bool = ...,
    gt: annotated_types.SupportsGt | None = ...,
    ge: annotated_types.SupportsGe | None = ...,
    lt: annotated_types.SupportsLt | None = ...,
    le: annotated_types.SupportsLe | None = ...,
    multiple_of: float | None = ...,
    strict: bool | None = ...,
    min_length: int | None = ...,
    max_length: int | None = ...,
    pattern: str | re.Pattern[str] | None = ...,
    allow_inf_nan: bool | None = ...,
    max_digits: int | None = ...,
    decimal_places: int | None = ...,
    description: str | None = ...,
    init: bool = True,
) -> Any: ...


@overload
def Field(
    *,
    id: bool = ...,
    gt: annotated_types.SupportsGt | None = ...,
    ge: annotated_types.SupportsGe | None = ...,
    lt: annotated_types.SupportsLt | None = ...,
    le: annotated_types.SupportsLe | None = ...,
    multiple_of: float | None = ...,
    strict: bool | None = ...,
    min_length: int | None = ...,
    max_length: int | None = ...,
    pattern: str | re.Pattern[str] | None = ...,
    allow_inf_nan: bool | None = ...,
    max_digits: int | None = ...,
    decimal_places: int | None = ...,
    description: str | None = ...,
    init: bool = True,
) -> Any: ...


def Field(default: Any = ..., **kwargs: Any) -> Any:
    id_flag = kwargs.pop("id", False)
    field_info = PField(default, **kwargs)
    if id_flag:
        existing = list(field_info.metadata)
        existing.append(_IDENTITY_MARKER)
        object.__setattr__(field_info, "metadata", existing)
    return field_info


@overload
def PrivateField(default: Any = ..., *, default_factory: None = None) -> Any: ...


@overload
def PrivateField(*, default_factory: Callable[[], Any]) -> Any: ...


def PrivateField(
    default: Any = Unset(), *, default_factory: Callable[[], Any] | None = None
) -> Any:
    if default_factory is not None:
        return PrivateAttr(default_factory=default_factory, init=False)
    return PrivateAttr(default=default, init=False)


def is_public_field(name: str) -> bool:
    return not name.startswith("_")
