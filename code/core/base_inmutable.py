from typing import Any

from .base_validator import BaseValidator


class BaseInmutable(BaseValidator):
    __initialized__: bool = False

    def __setattr__(self, name: str, value: Any) -> None:
        if self.__initialized__:
            raise ValueError("Cannot mutate this object")
        super().__setattr__(name, value)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__initialized__ = True
