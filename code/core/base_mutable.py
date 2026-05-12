import inspect
from contextlib import contextmanager
from enum import StrEnum
from functools import wraps
from typing import Any, Callable, Generator, Literal, Type, cast

from .base_validator import BaseValidator, PydanticFacadeMeta
from .domain_exception import MutationForbiddenError


class MutatingState(StrEnum):
    BLOCK = "block"
    PASS = "pass"
    SUPER = "super"


class MutatingContext:
    def __init__(self):
        self._deep_states = {
            MutatingState.PASS: 0,
            MutatingState.SUPER: 0,
        }

    def enter(
        self, state: Literal[MutatingState.PASS, MutatingState.SUPER]
    ) -> None:
        self._deep_states[state] += 1

    def exit(
        self, state: Literal[MutatingState.PASS, MutatingState.SUPER]
    ) -> None:
        self._deep_states[state] -= 1 if self._deep_states[state] > 0 else 0

    @property
    def status(
        self,
    ) -> Literal[MutatingState.BLOCK, MutatingState.PASS, MutatingState.SUPER]:
        return (
            MutatingState.SUPER
            if self._deep_states[MutatingState.SUPER] > 0
            else MutatingState.PASS
            if self._deep_states[MutatingState.PASS] > 0
            else MutatingState.BLOCK
        )


class MutableBaseMeta(PydanticFacadeMeta):
    NOT_MUTABLE_CALLABLES = {
        "can_mutate",
        "_get_mutating_context",
    }

    def __new__(mcls, name, bases, namespace):

        cls = super().__new__(mcls, name, bases, namespace)

        def mutate(fn: Callable) -> Callable:
            @wraps(fn)
            def wrapper(self: BaseMutable, *args: Any, **kwargs: Any) -> Any:
                super_mutate = fn.__name__.startswith("_")
                with self.__mutate__(super_mutate=super_mutate):
                    return fn(self, *args, **kwargs)

            setattr(wrapper, "__mutable__", True)

            return wrapper

        for base in cls.__mro__:
            for attr_name, attr_value in base.__dict__.items():
                if attr_name.startswith("__") and attr_name.endswith("__"):
                    continue
                if attr_name in cls.NOT_MUTABLE_CALLABLES or getattr(
                    attr_value, "__mutable__", False
                ):
                    continue
                if not inspect.isfunction(attr_value):
                    continue
                setattr(cls, attr_name, mutate(attr_value))
        return cls


class BaseMutable(BaseValidator, metaclass=MutableBaseMeta):
    __mutating_context__: MutatingContext | None = None
    __mutating_context_class__: Type[MutatingContext] = MutatingContext

    def can_mutate(self) -> bool:
        return True

    def _get_mutating_context(self) -> MutatingContext:
        if self.__mutating_context__ is None:
            object.__setattr__(
                self, "__mutating_context__", self.__mutating_context_class__()
            )
        return cast(MutatingContext, self.__mutating_context__)

    @contextmanager
    def __mutate__(
        self, super_mutate: bool = False
    ) -> Generator[None, None, None]:
        mutating_context = self._get_mutating_context()
        mutation: Literal[MutatingState.PASS, MutatingState.SUPER] = (
            MutatingState.SUPER if super_mutate else MutatingState.PASS
        )
        mutating_context.enter(mutation)
        yield
        mutating_context.exit(mutation)

    def __setattr__(self, name: str, value: Any) -> None:
        mutating_status = self._get_mutating_context().status
        super_mutate = mutating_status == MutatingState.SUPER
        pass_mutate = (
            mutating_status == MutatingState.PASS and self.can_mutate()
        )
        can_mutate = super_mutate or pass_mutate
        if not can_mutate:
            raise MutationForbiddenError()
        super().__setattr__(name, value)
