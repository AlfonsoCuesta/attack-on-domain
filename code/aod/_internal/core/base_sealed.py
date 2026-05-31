from typing import ClassVar, Literal, Type

from .base_guarded import BaseGuarded, MutatingContext, MutatingState


class MutatingContextBlock(MutatingContext):
    def enter(self, state: Literal[MutatingState.PASS, MutatingState.SUPER]) -> None:
        pass

    def exit(self, state: Literal[MutatingState.PASS, MutatingState.SUPER]) -> None:
        pass

    @property
    def status(
        self,
    ) -> Literal[MutatingState.BLOCK, MutatingState.PASS, MutatingState.SUPER]:
        return MutatingState.BLOCK


class BaseSealed(BaseGuarded):
    __mutating_context_class__: ClassVar[Type[MutatingContext]] = MutatingContextBlock
    __stop_context_mutating__: ClassVar[bool] = True

    def _can_mutate(self) -> bool:
        return False
