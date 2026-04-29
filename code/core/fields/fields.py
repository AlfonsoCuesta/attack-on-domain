import re
from typing import Any, Callable, Literal, overload

import annotated_types
from pydantic import Field as PField
from pydantic import PrivateAttr


class Unset:
    def __repr__(self) -> str:
        return "UNSET FIELD"


@overload
def Field(
    default: Any,
    *,
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
    init: bool = True,
) -> Any: ...


@overload
def Field(
    *,
    default_factory: Callable[[], Any],
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
    init: bool = True,
) -> Any: ...


@overload
def Field(
    *,
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
    init: bool = True,
) -> Any: ...


def Field(default: Any = ..., **kwargs: Any) -> Any:
    return PField(default, **kwargs)


@overload
def PrivateField(
    default: Any = ...,
    *,
    default_factory: None = None,
    init: Literal[False] = False,
    **kwargs: Any,
) -> Any: ...


@overload
def PrivateField(
    *,
    default_factory: Callable[[], Any],
    init: Literal[False] = False,
    **kwargs: Any,
) -> Any: ...


@overload
def PrivateField(
    default: Any = ...,
    *,
    default_factory: None = None,
    init: Literal[True],
    **kwargs: Any,
) -> Any: ...


@overload
def PrivateField(
    *,
    default_factory: Callable[[], Any],
    init: Literal[True],
    **kwargs: Any,
) -> Any: ...


def PrivateField(
    default: Any = ...,
    *,
    default_factory: Callable[[], Any] | None = None,
    **kwargs: Any,
) -> Any:
    init = kwargs.get("init", False)
    if default_factory is not None:
        return PrivateAttr(default_factory=default_factory, init=init)
    field_default = Unset() if default is ... else default
    return PrivateAttr(default=field_default, init=init)
