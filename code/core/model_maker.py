from typing import Annotated, Any, Type, get_args, get_origin

from pydantic import BaseModel, ConfigDict
from pydantic.fields import ModelPrivateAttr

from .validators import is_validator

VALIDATION_MODEL_KEY = "__validation_model__"
RAW_MODEL_KEY = "__raw_model__"


def get_parent_models(
    bases: tuple[Type[Any], ...], key: str
) -> tuple[Type[Any], ...]:
    parent_models = tuple(getattr(b, key) for b in bases if hasattr(b, key))
    if not parent_models:
        parent_models = (BaseModel,)
    return parent_models


def get_model_config(cls: Type[Any]) -> ConfigDict:
    existing_config = getattr(cls, "model_config", None)
    if isinstance(existing_config, dict):
        return ConfigDict(**existing_config, arbitrary_types_allowed=True)
    return ConfigDict(arbitrary_types_allowed=True)


def make_validation_model(
    cls: Type[Any],
    name: str,
    bases: tuple[Type[Any], ...],
) -> Type[BaseModel]:
    full_ns = {
        "model_config": get_model_config(cls),
        "__annotations__": cls.__annotations__,
        **{k: getattr(cls, k) for k in cls.__annotations__ if hasattr(cls, k)},
    }
    for k, v in cls.__dict__.copy().items():
        if validator_info := is_validator(v):
            full_ns[k] = validator_info(v)

    parent_models = get_parent_models(bases, VALIDATION_MODEL_KEY)
    return type(name + "ValidationModel", parent_models, full_ns)


def strip_validators(annotation):
    if get_origin(annotation) is Annotated:
        return get_args(annotation)[0]
    return annotation


def make_raw_model(
    cls: Type[Any],
    name: str,
    bases: tuple[Type[Any], ...],
) -> Type[BaseModel]:
    annotations = {
        k: strip_validators(v) for k, v in cls.__annotations__.items()
    }
    ns: dict[str, Any] = {
        "model_config": get_model_config(cls),
        "__annotations__": annotations,
    }

    for base in reversed(cls.__mro__):
        for k, v in getattr(base, "__dict__", {}).items():
            if isinstance(v, ModelPrivateAttr):
                ns[k] = v

    parent_models = get_parent_models(bases, RAW_MODEL_KEY)
    return type(name + "RawModel", parent_models, ns)
