import inspect
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, ClassVar, Generator, Literal, Type

from ..base_validator import (
    BaseValidator,
    PydanticFacadeMeta,
)
from ..domain_exception import MutationForbiddenException
from ..invariances.invariances import VALIDATOR_KEY
from .make_immutable import make_immutable
from .mutating_context import MutatingContext, MutatingState

MUTABLE_KEY = "__mutable__"


def is_dunder(name: str) -> bool:
    return name.startswith("__")


def mark_mutable(
    fn: Callable,
    state: Literal[MutatingState.PASS, MutatingState.SUPER] = MutatingState.PASS,
) -> Callable:
    setattr(fn, MUTABLE_KEY, state)
    return fn


def mutate(fn: Callable, *, super_mutate: bool = False) -> Callable:
    @wraps(fn)
    def wrapper(self: BaseMutable, *args: Any, **kwargs: Any) -> Any:
        with self.__mutate__(super_mutate=super_mutate):
            return fn(self, *args, **kwargs)

    mutate_state = MutatingState.SUPER if super_mutate else MutatingState.PASS
    return mark_mutable(wrapper, state=mutate_state)


def super_context(fn: Callable) -> Callable:
    return mutate(fn, super_mutate=True)


class MutableBaseMeta(PydanticFacadeMeta):
    def __new__(mcls, name, bases, namespace):

        cls = super().__new__(mcls, name, bases, namespace)
        super_attrs = {
            attr_name
            for base in cls.__mro__
            for attr_name, attr_value in base.__dict__.items()
            if getattr(attr_value, MUTABLE_KEY, False) == MutatingState.SUPER
        }

        for base in cls.__mro__:
            if base.__dict__.get("__stop_context_mutating__", False):
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

                super_mutate = attr_name in super_attrs
                setattr(cls, attr_name, mutate(attr_value, super_mutate=super_mutate))
        return cls


class BaseMutable(BaseValidator, metaclass=MutableBaseMeta):
    __mutating_context_class__: ClassVar[Type[MutatingContext]] = MutatingContext
    __stop_context_mutating__: ClassVar[bool] = True

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__mutating_context__ = self.__mutating_context_class__()
        self.__initialized__ = True

    @super_context
    def _can_mutate(self) -> bool:
        return True

    @property
    def _mutation_status(self) -> MutatingState:
        if not self._is_initialized:
            return MutatingState.SUPER
        return self.__mutating_context__.status

    @property
    def _is_initialized(self) -> bool:
        if not hasattr(self, "__initialized__"):
            return False
        return object.__getattribute__(self, "__initialized__")

    @contextmanager
    def __mutate__(self, super_mutate: bool = False) -> Generator[None, None, None]:
        mutating_context = self.__mutating_context__
        mutation: Literal[MutatingState.PASS, MutatingState.SUPER] = (
            MutatingState.SUPER if super_mutate else MutatingState.PASS
        )
        mutating_context.enter(mutation)
        yield
        mutating_context.exit(mutation)

    @property
    def _is_mutation_allowed(self) -> bool:
        mutating_status = self._mutation_status
        if mutating_status == MutatingState.BLOCK:
            return False
        if mutating_status == MutatingState.SUPER:
            return True
        return self._can_mutate()

    def __setattr__(self, name: str, value: Any) -> None:
        if not self._is_mutation_allowed:
            raise MutationForbiddenException(
                "Cannot mutate this object " + self.__class__.__name__
            )
        super().__setattr__(name, value)

    def __getattribute__(self, name):
        value = object.__getattribute__(self, name)
        if is_dunder(name):
            return value
        if name not in self.__model_fields__:
            return value
        if inspect.isfunction(value):
            return value

        if self._mutation_status == MutatingState.SUPER:
            return value
        if self._mutation_status == MutatingState.PASS and self._can_mutate():
            return value
        return make_immutable(value)
