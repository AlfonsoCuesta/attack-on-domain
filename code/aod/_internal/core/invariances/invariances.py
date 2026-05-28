import functools
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


def field_invariance(
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


def invariance(fn):
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        fn(self, *args, **kwargs)
        return self

    validator_info = ValidatorInfo(validation=pydantic_model_validator, mode="after")
    setattr(wrapper, VALIDATOR_KEY, validator_info)
    return wrapper


def is_validator(fn) -> ValidatorInfo | None:
    return _get_validator_key(fn, VALIDATOR_KEY)


def _get_validator_key(fn, key: str) -> ValidatorInfo | None:
    value = getattr(fn, key, None)
    if value is None and isinstance(fn, classmethod):
        return getattr(fn.__func__, key, None)
    return value
