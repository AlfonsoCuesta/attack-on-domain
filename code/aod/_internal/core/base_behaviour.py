from typing import ClassVar

from .base_guarded import BaseGuarded
from .base_guarded.mutating_context import MutatingContext, MutatingState


class BaseBehaviour(BaseGuarded):
    __skip_method_wrapping__: ClassVar[bool] = True

    @property
    def _mutation_status(self) -> MutatingState:
        status = MutatingContext.status(id(self))
        return MutatingState.INHERIT if status != MutatingState.BLOCK else MutatingState.BLOCK
