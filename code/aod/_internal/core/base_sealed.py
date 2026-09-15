from typing import ClassVar

from .base_guarded import BaseGuarded
from .base_guarded.mutating_context import MutatingContext, MutatingState


class BaseSealed(BaseGuarded):
    __skip_method_wrapping__: ClassVar[bool] = True

    def _can_mutate(self) -> bool:
        return False

    @property
    def _mutation_status(self) -> MutatingState:
        status = MutatingContext.status(id(self))
        return status if status == MutatingState.INHERIT else MutatingState.BLOCK
