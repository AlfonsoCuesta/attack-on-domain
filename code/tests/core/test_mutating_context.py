from aod._internal.core.base_mutable import MutatingContext, MutatingState


def test_mutating_context_state_transitions() -> None:
    ctx = MutatingContext()
    assert ctx.status == MutatingState.BLOCK

    ctx.enter(MutatingState.PASS)
    assert ctx.status == MutatingState.PASS

    ctx.enter(MutatingState.SUPER)
    assert ctx.status == MutatingState.SUPER

    ctx.exit(MutatingState.SUPER)
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


def test_mutating_context_status_returns_super_when_super_state_is_active() -> None:
    ctx = MutatingContext()
    ctx.enter(MutatingState.SUPER)
    assert ctx.status == MutatingState.SUPER


def test_mutating_context_status_anidated_super_states() -> None:
    ctx = MutatingContext()
    ctx.enter(MutatingState.SUPER)
    assert ctx.status == MutatingState.SUPER
    ctx.enter(MutatingState.SUPER)
    assert ctx.status == MutatingState.SUPER
    ctx.exit(MutatingState.SUPER)
    assert ctx.status == MutatingState.SUPER
    ctx.exit(MutatingState.SUPER)
    assert ctx.status == MutatingState.BLOCK


def test_mutating_context_status_anidated_pass_states() -> None:
    ctx = MutatingContext()
    ctx.enter(MutatingState.PASS)
    ctx.enter(MutatingState.SUPER)
    assert ctx.status == MutatingState.SUPER
    ctx.exit(MutatingState.PASS)
    assert ctx.status == MutatingState.SUPER


def test_mutating_context_status_exit_when_state_is_not_active() -> None:
    ctx = MutatingContext()
    ctx.exit(MutatingState.PASS)
    assert ctx.status == MutatingState.BLOCK
    ctx.exit(MutatingState.SUPER)
    assert ctx.status == MutatingState.BLOCK
