from enum import StrEnum
from typing import Literal


class MutatingState(StrEnum):
    BLOCK = "block"
    PASS = "pass"
    INHERIT = "inherit"


class MutatingContext:
    def __init__(self):
        self._deep_states = {
            MutatingState.PASS: 0,
            MutatingState.INHERIT: 0,
        }

    def enter(self, state: Literal[MutatingState.PASS, MutatingState.INHERIT]) -> None:
        self._deep_states[state] += 1

    def exit(self, state: Literal[MutatingState.PASS, MutatingState.INHERIT]) -> None:
        if self._deep_states[state] == 0:
            raise RuntimeError(f"Called exit({state!r}) without matching enter")
        self._deep_states[state] -= 1

    @property
    def status(
        self,
    ) -> Literal[MutatingState.BLOCK, MutatingState.PASS, MutatingState.INHERIT]:
        return (
            MutatingState.INHERIT
            if self._deep_states[MutatingState.INHERIT] > 0
            else (
                MutatingState.PASS
                if self._deep_states[MutatingState.PASS] > 0
                else MutatingState.BLOCK
            )
        )
