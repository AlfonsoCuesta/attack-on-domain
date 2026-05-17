import inspect
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Generator, Literal, Type, cast

from ..base_validator import BaseValidator, PydanticFacadeMeta
from ..domain_exception import MutationForbiddenError
from .immutable_object import make_immutable
from .mutating_context import MutatingContext, MutatingState


class MutableBaseMeta(PydanticFacadeMeta):
    NOT_MUTABLE_CALLABLES = {
        "can_mutate",
        "_get_mutating_context",
        "_mutating_status",
    }

    def __new__(mcls, name, bases, namespace):

        cls = super().__new__(mcls, name, bases, namespace)

        def mutate(fn: Callable) -> Callable:
            @wraps(fn)
            def wrapper(self: BaseMutable, *args: Any, **kwargs: Any) -> Any:
                super_mutate = getattr(fn, "__name__").startswith("_")
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

    @property
    def _mutation_status(self) -> MutatingState:
        return self._get_mutating_context().status

    @contextmanager
    def __mutate__(self, super_mutate: bool = False) -> Generator[None, None, None]:
        mutating_context = self._get_mutating_context()
        mutation: Literal[MutatingState.PASS, MutatingState.SUPER] = (
            MutatingState.SUPER if super_mutate else MutatingState.PASS
        )
        mutating_context.enter(mutation)
        yield
        mutating_context.exit(mutation)

    def __setattr__(self, name: str, value: Any) -> None:
        mutating_status = object.__getattribute__(self, "_mutation_status")
        super_mutate = mutating_status == MutatingState.SUPER
        pass_mutate = mutating_status == MutatingState.PASS and self.can_mutate()
        if not (super_mutate or pass_mutate):
            raise MutationForbiddenError()
        super().__setattr__(name, value)

    def __getattribute__(self, name):
        value = object.__getattribute__(self, name)
        if name.startswith("_"):
            return value
        if name not in object.__getattribute__(self, "__model_fields__"):
            return value

        mutating_status = object.__getattribute__(self, "_mutation_status")
        can_mutate = object.__getattribute__(self, "can_mutate")
        super_mutate = mutating_status == MutatingState.SUPER
        pass_mutate = mutating_status == MutatingState.PASS and can_mutate()
        if super_mutate or pass_mutate:
            return value
        return make_immutable(value)
