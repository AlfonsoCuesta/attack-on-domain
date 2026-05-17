from enum import StrEnum
from typing import Literal


class MutatingState(StrEnum):
    BLOCK = "block"
    PASS = "pass"
    SUPER = "super"


class MutatingContext:
    def __init__(self):
        self._deep_states = {
            MutatingState.PASS: 0,
            MutatingState.SUPER: 0,
        }

    def enter(self, state: Literal[MutatingState.PASS, MutatingState.SUPER]) -> None:
        self._deep_states[state] += 1

    def exit(self, state: Literal[MutatingState.PASS, MutatingState.SUPER]) -> None:
        self._deep_states[state] -= 1 if self._deep_states[state] > 0 else 0

    @property
    def status(
        self,
    ) -> Literal[MutatingState.BLOCK, MutatingState.PASS, MutatingState.SUPER]:
        return (
            MutatingState.SUPER
            if self._deep_states[MutatingState.SUPER] > 0
            else MutatingState.PASS
            if self._deep_states[MutatingState.PASS] > 0
            else MutatingState.BLOCK
        )
