import pytest

from aod._internal.core.base_guarded import MutatingContext, MutatingState


def test_mutating_context_state_transitions() -> None:
    ctx = MutatingContext()
    assert ctx.status == MutatingState.BLOCK

    ctx.enter(MutatingState.PASS)
    assert ctx.status == MutatingState.PASS

    ctx.enter(MutatingState.INHERIT)
    assert ctx.status == MutatingState.INHERIT

    ctx.exit(MutatingState.INHERIT)
    assert ctx.status == MutatingState.PASS

    ctx.exit(MutatingState.PASS)
    assert ctx.status == MutatingState.BLOCK


def test_mutating_context_status_returns_block_when_no_states_are_active() -> None:
    ctx = MutatingContext()
    assert ctx.status == MutatingState.BLOCK


def test_mutating_context_status_returns_pass_when_pass_state_is_active() -> None:
    ctx = MutatingContext()
    ctx.enter(MutatingState.PASS)
    assert ctx.status == MutatingState.PASS


def test_mutating_context_status_returns_inherit_when_inherit_state_is_active() -> None:
    ctx = MutatingContext()
    ctx.enter(MutatingState.INHERIT)
    assert ctx.status == MutatingState.INHERIT


def test_mutating_context_status_anidated_inherit_states() -> None:
    ctx = MutatingContext()
    ctx.enter(MutatingState.INHERIT)
    assert ctx.status == MutatingState.INHERIT
    ctx.enter(MutatingState.INHERIT)
    assert ctx.status == MutatingState.INHERIT
    ctx.exit(MutatingState.INHERIT)
    assert ctx.status == MutatingState.INHERIT
    ctx.exit(MutatingState.INHERIT)
    assert ctx.status == MutatingState.BLOCK


def test_mutating_context_status_anidated_pass_states() -> None:
    ctx = MutatingContext()
    ctx.enter(MutatingState.PASS)
    ctx.enter(MutatingState.INHERIT)
    assert ctx.status == MutatingState.INHERIT
    ctx.exit(MutatingState.PASS)
    assert ctx.status == MutatingState.INHERIT


def test_mutating_context_status_exit_raises_when_state_is_not_active() -> None:
    ctx = MutatingContext()
    with pytest.raises(RuntimeError, match="exit.*PASS.*without matching enter"):
        ctx.exit(MutatingState.PASS)
    with pytest.raises(RuntimeError, match="exit.*INHERIT.*without matching enter"):
        ctx.exit(MutatingState.INHERIT)
