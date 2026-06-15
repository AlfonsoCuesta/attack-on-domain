import functools
from typing import Any, Callable, Literal

from pydantic import (
    field_validator as pydantic_field_validator,
)
from pydantic import (
    model_validator as pydantic_model_validator,
)

from ..domain_exception import InvarianceException

VALIDATOR_KEY = "__field_validator_info__"


class ValidatorInfo:
    def __init__(
        self,
        *args,
        validation: Callable,
        name: str | None = None,
        is_invariance: bool = False,
        **kwargs,
    ):
        self.args = args
        self.kwargs = kwargs
        self.validation = validation
        self.name = name
        self.is_invariance = is_invariance

    def __call__(self, fn):
        return self.validation(*self.args, **self.kwargs)(fn)


def field_invariance(
    *fields,
    mode: Literal["before", "after"] = "before",
    check_fields: bool = False,
    name: str | None = None,
):
    def decorator(fn):
        if not isinstance(fn, classmethod):
            fn = classmethod(fn)
        original: Any = fn.__func__

        def wrapper(cls: type, value: Any) -> Any:
            try:
                return original(cls, value)
            except (ValueError, AssertionError) as e:
                raise InvarianceException(name or original.__name__, str(e)) from None

        wrapper.__name__ = original.__name__
        wrapper.__qualname__ = original.__qualname__
        wrapper.__module__ = original.__module__

        wrapped_cm = classmethod(wrapper)
        setattr(
            wrapped_cm,
            VALIDATOR_KEY,
            ValidatorInfo(
                validation=pydantic_field_validator,
                *fields,
                mode=mode,
                check_fields=check_fields,
                name=name,
                is_invariance=True,
            ),
        )
        return wrapped_cm

    return decorator


def invariance(fn=None, *, name: str | None = None):
    if fn is None:
        return lambda f: invariance(f, name=name)

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            fn(self, *args, **kwargs)
            return self
        except (ValueError, AssertionError) as e:
            raise InvarianceException(name or fn.__name__, str(e)) from None

    validator_info = ValidatorInfo(
        validation=pydantic_model_validator,
        mode="after",
        name=name,
        is_invariance=True,
    )
    setattr(wrapper, VALIDATOR_KEY, validator_info)
    return wrapper


def is_validator(fn) -> ValidatorInfo | None:
    return _get_validator_key(fn, VALIDATOR_KEY)


def _get_validator_key(fn, key: str) -> ValidatorInfo | None:
    value = getattr(fn, key, None)
    if value is None and isinstance(fn, classmethod):
        return getattr(fn.__func__, key, None)
    return value
