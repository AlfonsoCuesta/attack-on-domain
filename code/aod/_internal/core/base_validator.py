import contextvars
import inspect
from abc import ABCMeta
from typing import Any, Callable, ClassVar, Self, Type, dataclass_transform

from pydantic import BaseModel, ValidationError

from .domain_exception import InvarianceException, ModelValidationError
from .fields import Field
from .invariances import is_validator
from .model_maker import (
    RAW_MODEL_KEY,
    VALIDATION_MODEL_KEY,
    make_raw_model,
    make_validation_model,
)

_use_raw_model: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_use_raw_model", default=False
)

VALIDATION_REGISTRY_KEY = "__validator_registry__"


class ValidationModelMeta(ABCMeta):
    def __new__(mcls, name, bases, namespace, **kwargs: Any):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)

        validation_model = make_validation_model(cls, name, bases)
        raw_model = make_raw_model(cls, name, bases)

        setattr(cls, VALIDATION_MODEL_KEY, validation_model)
        setattr(cls, RAW_MODEL_KEY, raw_model)
        setattr(cls, "__model_fields__", validation_model.model_fields)

        setattr(cls.__init__, "__signature__", inspect.signature(validation_model))

        # Build validator registry from this class's namespace
        registry: dict[str, Callable[..., Any]] = {}
        for k, v in namespace.items():
            if info := is_validator(v):
                validator_name = info.name or k
                registry[validator_name] = v

        # Merge with parent registries (child overrides parent)
        for base in bases:
            parent_registry = getattr(base, VALIDATION_REGISTRY_KEY, {})
            for rk, rv in parent_registry.items():
                if rk not in registry:
                    registry[rk] = rv

        setattr(cls, VALIDATION_REGISTRY_KEY, registry)

        return cls


@dataclass_transform(field_specifiers=(Field,), kw_only_default=True)
class BaseValidator(metaclass=ValidationModelMeta):
    __validation_model__: ClassVar[Type[BaseModel]]
    __raw_model__: ClassVar[Type[BaseModel]]
    __model_fields__: ClassVar[dict[str, Any]]
    __validator_registry__: ClassVar[dict[str, Callable[..., Any]]]

    def __init__(self, **kwargs: Any) -> None:
        if _use_raw_model.get():
            model = self.__class__.__raw_model__
        else:
            model = self.__class__.__validation_model__

        try:
            validated = model(**kwargs)
        except ValidationError as e:
            for error in e.errors():
                cause = error.get("ctx", {}).get("error")
                if isinstance(cause, InvarianceException):
                    raise cause from e
            raise ModelValidationError(self.__class__.__name__, str(e)) from e

        self.__set_model_attributes(validated)
        if not _use_raw_model.get():
            self.__post_init__()

    def __post_init__(self) -> None:
        pass

    def copy(self, **overrides: Any) -> Self:
        current = {}
        for k in self.__model_fields__:
            current[k] = getattr(self, k)
        current.update(overrides)
        return self.__class__(**current)

    def __set_model_attributes(self, validated: BaseModel) -> None:
        for k, v in validated.model_dump().items():
            object.__setattr__(self, k, v)

        private = getattr(validated, "__pydantic_private__", {})
        if private:
            for k, v in private.items():
                object.__setattr__(self, k, v)

    def __repr__(self) -> str:
        fields = self.__validation_model__.model_fields.keys()
        args = ", ".join(f"{k}={getattr(self, k)!r}" for k in fields)
        return f"{self.__class__.__name__}({args})"
