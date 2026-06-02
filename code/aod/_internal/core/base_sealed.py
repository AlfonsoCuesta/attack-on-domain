from typing import ClassVar

from .base_guarded import BaseGuarded, MutatingState


class BaseSealed(BaseGuarded):
    __skip_method_wrapping__: ClassVar[bool] = True

    def _can_mutate(self) -> bool:
        return False

    @property
    def _mutation_status(self) -> MutatingState:
        status = self.__mutating_context__.status
        return status if status == MutatingState.INHERIT else MutatingState.BLOCK
