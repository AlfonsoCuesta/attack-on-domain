from typing import Callable, Literal

from pydantic import (
    field_validator as pydantic_field_validator,
)
from pydantic import (
    model_validator as pydantic_model_validator,
)

VALIDATOR_KEY = "__field_validator_info__"


class ValidatorInfo:
    def __init__(self, *args, validation: Callable, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.validation = validation

    def __call__(self, fn):
        return self.validation(*self.args, **self.kwargs)(fn)


def field_validator(
    *fields,
    mode: Literal["before", "after"] = "before",
    check_fields: bool = False,
):
    def decorator(fn):
        if not isinstance(fn, classmethod):
            fn = classmethod(fn)
        setattr(
            fn,
            VALIDATOR_KEY,
            ValidatorInfo(
                validation=pydantic_field_validator,
                *fields,
                mode=mode,
                check_fields=check_fields,
            ),
        )
        return fn

    return decorator


def post_init(fn):
    setattr(
        fn,
        VALIDATOR_KEY,
        ValidatorInfo(validation=pydantic_model_validator, mode="after"),
    )
    return fn


def is_validator(fn) -> ValidatorInfo | None:
    has_key = getattr(fn, VALIDATOR_KEY, None)
    if not has_key and isinstance(fn, classmethod):
        has_key = getattr(fn.__func__, VALIDATOR_KEY, None)
    return has_key
