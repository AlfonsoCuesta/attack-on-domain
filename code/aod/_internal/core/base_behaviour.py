from typing import ClassVar

from .base_guarded import BaseGuarded, MutatingState


class BaseBehaviour(BaseGuarded):
    __skip_method_wrapping__: ClassVar[bool] = True

    @property
    def _mutation_status(self) -> MutatingState:
        status = self.__mutating_context__.status
        return MutatingState.INHERIT if status != MutatingState.BLOCK else MutatingState.BLOCK
