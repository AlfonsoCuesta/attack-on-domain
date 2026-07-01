from __future__ import annotations

from typing import TypeVar

from aod._internal.core.base_validator import BaseValidator
from aod._internal.core.model_maker import CONSTRAINED_MODEL_KEY
from pydantic import BaseModel

T = TypeVar("T", bound=BaseValidator)


def get_base_model(cls: type[T]) -> type[BaseModel]:
    """Return the constrained Pydantic BaseModel for a BaseGuarded subclass.

    Every BaseGuarded class (Entity, RootEntity, ValueObject) has an internal
    constrained model that is a Pydantic BaseModel with field definitions and
    field-level validators but no invariance validators. This function exposes
    it for use with FastAPI, Pydantic settings, and other BaseModel consumers.

    Example::

        from aod.domain.validation import get_base_model

        UserDTO = get_base_model(User)
        data = UserDTO(id=1, name="Alice", address={"street": "Main"})
    """
    return getattr(cls, CONSTRAINED_MODEL_KEY)
