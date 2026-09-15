from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Literal


class MutatingState(StrEnum):
    BLOCK = "block"
    PASS = "pass"
    INHERIT = "inherit"


@dataclass(frozen=True)
class _MutationDepth:
    """The nesting depth of a single guarded object in one execution context."""

    pass_depth: int = 0
    inherit_depth: int = 0


class MutatingContext:
    """Task-local mutation state, keyed by a guarded object's identity.

    The value stored in the ``ContextVar`` is never mutated in place.  This is
    important because an asyncio task inherits its parent's context when it is
    created; replacing the mapping keeps later changes isolated to that task.
    """

    _depths: ClassVar[ContextVar[dict[int, _MutationDepth]]] = ContextVar(
        "aod_mutation_depths", default={}
    )

    @classmethod
    def enter(
        cls,
        instance_id: int,
        state: Literal[MutatingState.PASS, MutatingState.INHERIT],
    ) -> None:
        depths = cls._depths.get()
        current = depths.get(instance_id, _MutationDepth())
        updated = (
            _MutationDepth(current.pass_depth + 1, current.inherit_depth)
            if state == MutatingState.PASS
            else _MutationDepth(current.pass_depth, current.inherit_depth + 1)
        )
        cls._depths.set({**depths, instance_id: updated})

    @classmethod
    def exit(
        cls,
        instance_id: int,
        state: Literal[MutatingState.PASS, MutatingState.INHERIT],
    ) -> None:
        depths = cls._depths.get()
        current = depths.get(instance_id, _MutationDepth())
        depth = current.pass_depth if state == MutatingState.PASS else current.inherit_depth
        if depth == 0:
            raise RuntimeError(f"Called exit({state!r}) without matching enter")

        updated = (
            _MutationDepth(current.pass_depth - 1, current.inherit_depth)
            if state == MutatingState.PASS
            else _MutationDepth(current.pass_depth, current.inherit_depth - 1)
        )
        next_depths = dict(depths)
        if updated == _MutationDepth():
            next_depths.pop(instance_id, None)
        else:
            next_depths[instance_id] = updated
        cls._depths.set(next_depths)

    @classmethod
    def status(
        cls, instance_id: int
    ) -> Literal[MutatingState.BLOCK, MutatingState.PASS, MutatingState.INHERIT]:
        depth = cls._depths.get().get(instance_id, _MutationDepth())
        if depth.inherit_depth:
            return MutatingState.INHERIT
        if depth.pass_depth:
            return MutatingState.PASS
        return MutatingState.BLOCK
