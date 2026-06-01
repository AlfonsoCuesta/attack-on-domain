import inspect
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, ClassVar, Generator, Literal, Type, cast

from ..base_validator import (
    BaseValidator,
    _use_raw_model,
)
from ..domain_exception import MutationForbiddenException
from ..invariances.invariances import VALIDATOR_KEY
from .make_immutable import make_immutable
from .mutating_context import MutatingContext, MutatingState

MUTABLE_KEY = "__mutable__"


def is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def mark_mutable(
    fn: Callable,
    state: Literal[MutatingState.PASS, MutatingState.INHERIT] = MutatingState.PASS,
) -> Callable:
    setattr(fn, MUTABLE_KEY, state)
    return fn


def mutate(fn: Callable, *, inherit_mutate: bool = False) -> Callable:
    @wraps(fn)
    def wrapper(self: BaseGuarded, *args: Any, **kwargs: Any) -> Any:
        with self.__mutate__(inherit_mutate=inherit_mutate):
            return fn(self, *args, **kwargs)

    mutate_state = cast(
        Literal[MutatingState.PASS, MutatingState.INHERIT],
        MutatingState.INHERIT if inherit_mutate else MutatingState.PASS,
    )
    return mark_mutable(wrapper, state=mutate_state)


def inherit_context(fn: Callable) -> Callable:
    return mutate(fn, inherit_mutate=True)


def _wrap_public_methods(cls: type) -> None:
    super_attrs = {
        attr_name
        for base in cls.__mro__
        for attr_name, attr_value in base.__dict__.items()
        if getattr(attr_value, MUTABLE_KEY, False) == MutatingState.INHERIT
    }

    for base in cls.__mro__:
        if base.__dict__.get("__skip_method_wrapping__", False):
            break
        for attr_name, attr_value in base.__dict__.items():
            if not inspect.isfunction(attr_value):
                continue
            if is_dunder(attr_name):
                continue
            if inspect.ismethod(attr_value):
                continue
            if getattr(attr_value, VALIDATOR_KEY, False):
                continue
            if getattr(attr_value, MUTABLE_KEY, False):
                continue

            inherit_mutate = attr_name in super_attrs
            setattr(cls, attr_name, mutate(attr_value, inherit_mutate=inherit_mutate))


class BaseGuarded(BaseValidator):
    __mutating_context_class__: ClassVar[Type[MutatingContext]] = MutatingContext
    __skip_method_wrapping__: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _wrap_public_methods(cls)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__mutating_context__ = self.__mutating_context_class__()
        if not _use_raw_model.get():
            self.__post_init__()
        self.__initialized__ = True

    @inherit_context
    def _can_mutate(self) -> bool:
        return True

    @property
    def _mutation_status(self) -> MutatingState:
        if not self._is_initialized:
            return MutatingState.INHERIT
        return self.__mutating_context__.status

    @property
    def _is_initialized(self) -> bool:
        if not hasattr(self, "__initialized__"):
            return False
        return object.__getattribute__(self, "__initialized__")

    @contextmanager
    def __mutate__(self, inherit_mutate: bool = False) -> Generator[None, None, None]:
        mutating_context = self.__mutating_context__
        mutation: Literal[MutatingState.PASS, MutatingState.INHERIT] = (
            MutatingState.INHERIT if inherit_mutate else MutatingState.PASS
        )
        mutating_context.enter(mutation)
        yield
        mutating_context.exit(mutation)

    @property
    def _is_mutation_allowed(self) -> bool:
        mutating_status = self._mutation_status
        if mutating_status == MutatingState.BLOCK:
            return False
        if mutating_status == MutatingState.INHERIT:
            return True
        return self._can_mutate()

    def __setattr__(self, name: str, value: Any) -> None:
        if not self._is_mutation_allowed:
            raise MutationForbiddenException("Cannot mutate this object " + self.__class__.__name__)
        super().__setattr__(name, value)

    def __getattribute__(self, name):
        value = object.__getattribute__(self, name)
        if is_dunder(name):
            return value
        if name not in self.__model_fields__:
            return value
        if inspect.isfunction(value):
            return value

        status = self._mutation_status
        if status == MutatingState.INHERIT or (status == MutatingState.PASS and self._can_mutate()):
            return value
        return make_immutable(value)
