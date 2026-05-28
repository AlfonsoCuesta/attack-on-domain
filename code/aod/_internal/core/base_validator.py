import contextvars
import inspect
from typing import Any, ClassVar, Self, Type, dataclass_transform

from pydantic import BaseModel

from .fields import Field
from .model_maker import (
    RAW_MODEL_KEY,
    VALIDATION_MODEL_KEY,
    make_raw_model,
    make_validation_model,
)

_use_raw_model: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_use_raw_model", default=False
)


class PydanticFacadeMeta(type):
    def __new__(mcls, name, bases, namespace):
        cls = super().__new__(mcls, name, bases, namespace)

        validation_model = make_validation_model(cls, name, bases)
        raw_model = make_raw_model(cls, name, bases)

        setattr(cls, VALIDATION_MODEL_KEY, validation_model)
        setattr(cls, RAW_MODEL_KEY, raw_model)
        setattr(cls, "__model_fields__", validation_model.model_fields)

        setattr(cls.__init__, "__signature__", inspect.signature(validation_model))

        return cls


@dataclass_transform(field_specifiers=(Field,), kw_only_default=True)
class BaseValidator(metaclass=PydanticFacadeMeta):
    __validation_model__: ClassVar[Type[BaseModel]]
    __raw_model__: ClassVar[Type[BaseModel]]
    __model_fields__: ClassVar[dict[str, Any]]

    def __init__(self, **kwargs: Any) -> None:
        if _use_raw_model.get():
            model = self.__class__.__raw_model__
        else:
            model = self.__class__.__validation_model__

        validated = model(**kwargs)

        self.__set_model_attributes(validated)

    def __set_model_attributes(self, validated: BaseModel) -> None:
        for k, v in validated.model_dump().items():
            object.__setattr__(self, k, v)

        private = getattr(validated, "__pydantic_private__", {})
        if private:
            for k, v in private.items():
                object.__setattr__(self, k, v)

    def __repr__(self):
        fields = self.__validation_model__.model_fields.keys()
        args = ", ".join(f"{k}={getattr(self, k)!r}" for k in fields)
        return f"{self.__class__.__name__}({args})"

    @classmethod
    def from_existing(cls, **kwargs) -> Self:
        token = _use_raw_model.set(True)
        try:
            return cls(**kwargs)
        finally:
            _use_raw_model.reset(token)
