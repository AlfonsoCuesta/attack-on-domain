from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from aod._internal.application.projection import Projection
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.type_handlers.generic_utils import validate_handler_subclass

P = TypeVar("P", bound=Projection)


class ProjectionHandler(BaseSealed, Generic[P]):
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        validate_handler_subclass(cls, ProjectionHandler, Projection)

    @abstractmethod
    def handle(self, projection: P) -> object: ...
