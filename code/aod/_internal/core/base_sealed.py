from typing import ClassVar, Literal, Type

from .base_guarded import BaseGuarded, MutatingContext, MutatingState


class MutatingContextBlock(MutatingContext):
    def enter(self, state: Literal[MutatingState.PASS, MutatingState.INHERIT]) -> None:
        pass

    def exit(self, state: Literal[MutatingState.PASS, MutatingState.INHERIT]) -> None:
        pass

    @property
    def status(
        self,
    ) -> Literal[MutatingState.BLOCK, MutatingState.PASS, MutatingState.INHERIT]:
        return MutatingState.BLOCK


class BaseSealed(BaseGuarded):
    __mutating_context_class__: ClassVar[Type[MutatingContext]] = MutatingContextBlock
    __skip_method_wrapping__: ClassVar[bool] = True

    def _can_mutate(self) -> bool:
        return False
