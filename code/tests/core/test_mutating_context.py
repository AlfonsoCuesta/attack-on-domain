import pytest

from aod._internal.core.base_guarded import MutatingContext, MutatingState


def test_mutating_context_state_transitions() -> None:
    instance_id = 1
    assert MutatingContext.status(instance_id) == MutatingState.BLOCK

    MutatingContext.enter(instance_id, MutatingState.PASS)
    assert MutatingContext.status(instance_id) == MutatingState.PASS

    MutatingContext.enter(instance_id, MutatingState.INHERIT)
    assert MutatingContext.status(instance_id) == MutatingState.INHERIT

    MutatingContext.exit(instance_id, MutatingState.INHERIT)
    assert MutatingContext.status(instance_id) == MutatingState.PASS

    MutatingContext.exit(instance_id, MutatingState.PASS)
    assert MutatingContext.status(instance_id) == MutatingState.BLOCK


def test_mutating_context_status_returns_block_when_no_states_are_active() -> None:
    assert MutatingContext.status(2) == MutatingState.BLOCK


def test_mutating_context_status_returns_pass_when_pass_state_is_active() -> None:
    instance_id = 3
    MutatingContext.enter(instance_id, MutatingState.PASS)
    assert MutatingContext.status(instance_id) == MutatingState.PASS
    MutatingContext.exit(instance_id, MutatingState.PASS)


def test_mutating_context_status_returns_inherit_when_inherit_state_is_active() -> None:
    instance_id = 4
    MutatingContext.enter(instance_id, MutatingState.INHERIT)
    assert MutatingContext.status(instance_id) == MutatingState.INHERIT
    MutatingContext.exit(instance_id, MutatingState.INHERIT)


def test_mutating_context_status_nested_inherit_states() -> None:
    instance_id = 5
    MutatingContext.enter(instance_id, MutatingState.INHERIT)
    assert MutatingContext.status(instance_id) == MutatingState.INHERIT
    MutatingContext.enter(instance_id, MutatingState.INHERIT)
    assert MutatingContext.status(instance_id) == MutatingState.INHERIT
    MutatingContext.exit(instance_id, MutatingState.INHERIT)
    assert MutatingContext.status(instance_id) == MutatingState.INHERIT
    MutatingContext.exit(instance_id, MutatingState.INHERIT)
    assert MutatingContext.status(instance_id) == MutatingState.BLOCK


def test_mutating_context_status_nested_pass_states() -> None:
    instance_id = 6
    MutatingContext.enter(instance_id, MutatingState.PASS)
    MutatingContext.enter(instance_id, MutatingState.INHERIT)
    assert MutatingContext.status(instance_id) == MutatingState.INHERIT
    MutatingContext.exit(instance_id, MutatingState.PASS)
    assert MutatingContext.status(instance_id) == MutatingState.INHERIT
    MutatingContext.exit(instance_id, MutatingState.INHERIT)


def test_mutating_context_status_exit_raises_when_state_is_not_active() -> None:
    with pytest.raises(RuntimeError, match="exit.*PASS.*without matching enter"):
        MutatingContext.exit(7, MutatingState.PASS)
    with pytest.raises(RuntimeError, match="exit.*INHERIT.*without matching enter"):
        MutatingContext.exit(7, MutatingState.INHERIT)
