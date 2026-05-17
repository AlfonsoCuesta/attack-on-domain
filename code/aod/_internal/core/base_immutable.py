from typing import Any, Literal

from .base_mutable import BaseMutable, MutatingContext, MutatingState


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


class BaseImmutable(BaseMutable):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        object.__setattr__(self, "__mutating_context_class__", MutatingContextBlock)

    def _can_mutate(self) -> bool:
        return False
