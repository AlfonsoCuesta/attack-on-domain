from __future__ import annotations

import pytest
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.handler import CommandPort
from aod._internal.application.logger import Logger
from aod._internal.application.contracts import Command
from aod._internal.application.use_case import AsyncUseCase as UseCase
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.core.fields.fields import PrivateField
from aod._internal.infrastructure.handlers.handlers import BaseHandler, CommandHandler
from aod._internal.infrastructure.session import AsyncSession, Session
from aod.testing.doubles import port_stub
from tests.application._use_case_scenarios import (
    _RUN_BODIES,
    SCENARIOS,
    Address,
    Scenario,
    User,
    UserCreated,
    UserRenamed,
    run_uc,
)


class _TxTestSession(AsyncSession):
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)

    async def begin(self) -> None:
        pass

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        self._rolled_back = True

    async def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return True

    async def execute(self, operation: object) -> object:
        return operation

    async def query(self, operation: object) -> object:
        return operation


class _TxSyncSession(Session):
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)

    def begin(self) -> None:
        pass

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        self._rolled_back = True

    def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return True

    def execute(self, operation: object) -> object:
        return operation

    def query(self, operation: object) -> object:
        return operation


class _TxHandler(BaseHandler):
    session: _TxTestSession


class _TxSyncSessionHandler(BaseHandler):
    session: _TxSyncSession


class _SaveUser(Command[User, None]):
    name: str


class _SaveHandler(CommandHandler[_SaveUser]):
    session: _TxSyncSession

    def handle(self, command: _SaveUser) -> None: ...


class _MyUC(UseCase):
    save: CommandPort[_SaveUser]

    async def run(self) -> None: ...


class CreateUser(UseCase):
    async def run(self, user_id: int, name: str) -> None:
        user = User(id=user_id, name=name)
        user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))


async def test_async_use_case_is_abstract() -> None:
    with pytest.raises(TypeError):
        UseCase()


async def test_subclass_without_run_is_abstract() -> None:
    class Incomplete(UseCase):
        pass

    with pytest.raises(TypeError):
        Incomplete()


async def test_subclass_with_run_can_be_instantiated() -> None:
    CreateUser()


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
async def test_scenario(scenario: Scenario) -> None:
    body = _RUN_BODIES[scenario.name]
    ns = {"run": lambda self, *args, **kwargs: body(self, *args, **kwargs)}
    cls = type(scenario.name, (UseCase,), ns)
    uc = cls()
    if scenario.expected_exception is not None:
        with pytest.raises(scenario.expected_exception):
            await run_uc(uc, **scenario.kwargs)
    else:
        await run_uc(uc, **scenario.kwargs)
    assert len(uc.events) == scenario.expected_events


async def test_events_is_empty_before_run() -> None:
    uc = CreateUser()
    assert uc.events == []


async def test_events_is_empty_after_init_even_without_call() -> None:
    class NoOp(UseCase):
        async def run(self) -> None:
            pass

    uc = NoOp()
    assert uc.events == []


async def test_run_collects_events_from_entity() -> None:
    uc = CreateUser()
    await uc.run(user_id=1, name="Alice")
    assert len(uc.events) == 1
    assert isinstance(uc.events[0], UserCreated)
    assert uc.events[0].user_id == 1
    assert uc.events[0].name == "Alice"


async def test_run_collects_multiple_events_from_entity() -> None:
    class MultiEmit(UseCase):
        async def run(self, user_id: int) -> None:
            user = User(id=user_id, name="Alice")
            user.rename("Bob")
            user.rename("Charlie")

    uc = MultiEmit()
    await uc.run(user_id=1)
    assert len(uc.events) == 2
    assert all(isinstance(e, UserRenamed) for e in uc.events)
    assert uc.events[0].new_name == "Bob"
    assert uc.events[1].new_name == "Charlie"


async def test_run_replaces_previous_events() -> None:
    uc = CreateUser()
    await uc.run(user_id=1, name="Alice")
    assert len(uc.events) == 1
    await uc.run(user_id=2, name="Bob")
    assert len(uc.events) == 1


async def test_run_with_no_events_keeps_empty_list() -> None:
    class NoOp(UseCase):
        async def run(self) -> None:
            pass

    uc = NoOp()
    await uc.run()
    assert uc.events == []


async def test_run_takes_parameters() -> None:
    captured: list[int] = []

    class Stateful(UseCase):
        async def run(self, value: int) -> None:
            captured.append(value)

    uc = Stateful()
    await uc.run(value=42)
    assert captured == [42]


async def test_subclass_can_have_private_methods() -> None:
    class WithHelper(UseCase):
        async def _double(self, n: int) -> int:
            return n * 2

        async def run(self, user_id: int) -> None:
            assert await self._double(user_id) == 4

    await WithHelper().run(user_id=2)


async def test_subclass_with_complex_init_state() -> None:
    class Complex(UseCase):
        async def run(self, user_id: int, address: Address) -> None:
            user = User(id=user_id, name="Alice", address=address)
            user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))

    addr = Address(street="Main St", city="Springfield")
    uc = Complex()
    await uc.run(user_id=1, address=addr)
    assert len(uc.events) == 1


async def test_run_is_wrapped_automatically() -> None:
    class MyUseCase(UseCase):
        async def run(self) -> None:
            pass

    uc = MyUseCase()
    await uc.run()


async def test_events_is_immutable_from_outside() -> None:
    uc = CreateUser()
    await uc.run(user_id=1, name="Alice")
    assert len(uc.events) == 1
    with pytest.raises(MutationForbiddenException):
        uc.events.append(UserCreated(user_id=2, name="Bob"))
    with pytest.raises(MutationForbiddenException):
        uc.events = []


async def test_run_exception_still_collects_emitted_events() -> None:
    class FailAfterEmit(UseCase):
        async def run(self, user_id: int) -> None:
            user = User(id=user_id, name="Alice")
            user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))
            msg = "boom"
            raise ValueError(msg)

    uc = FailAfterEmit()
    with pytest.raises(ValueError, match="boom"):
        await uc.run(user_id=1)
    assert len(uc.events) == 1


async def test_run_exception_no_emit_keeps_events_empty() -> None:
    class FailFast(UseCase):
        async def run(self) -> None:
            msg = "fail"
            raise ValueError(msg)

    uc = FailFast()
    with pytest.raises(ValueError, match="fail"):
        await uc.run()
    assert uc.events == []


async def test_events_not_shared_across_instances() -> None:
    uc1 = CreateUser()
    uc2 = CreateUser()
    await uc1.run(user_id=1, name="Alice")
    assert len(uc1.events) == 1
    assert uc2.events == []


async def test_tx_auto_commit_on_success() -> None:
    session = _TxTestSession()
    handler = _TxHandler(session=session)

    class Create(UseCase):
        __skip_port_check__ = True
        save: _TxHandler

        async def run(self) -> None:
            pass

    uc = Create(save=handler)
    await uc.run()
    assert session._committed
    assert not session._rolled_back


async def test_tx_auto_rollback_on_failure() -> None:
    session = _TxTestSession()
    handler = _TxHandler(session=session)

    class Fail(UseCase):
        __skip_port_check__ = True
        save: _TxHandler

        async def run(self) -> None:
            raise ValueError("oops")

    uc = Fail(save=handler)
    with pytest.raises(ValueError):
        await uc.run()
    assert session._rolled_back
    assert not session._committed


async def test_logger_auto_logs_completion() -> None:
    class Simple(UseCase):
        logger: Logger

        async def run(self) -> None:
            pass

    logger = port_stub(Logger)()
    uc = Simple(logger=logger)
    await uc.run()
    completions = [c for c in logger.info.call_args_list if "completed" in str(c.args[0])]
    assert len(completions) == 1


async def test_event_bus_auto_publishes_on_success() -> None:
    class Emit(UseCase):
        event_bus: EventBus

        async def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="test"))

    bus = port_stub(EventBus)()
    uc = Emit(event_bus=bus)
    await uc.run()
    assert bus.publish.call_count == 1


async def test_commit_failure_rolls_back_and_logs() -> None:
    class _FailOnCommitSession(_TxTestSession):
        async def commit(self) -> None:
            raise RuntimeError("commit failed")

    session = _FailOnCommitSession()
    handler = _TxHandler(session=session)

    class Simple(UseCase):
        __skip_port_check__ = True
        logger: Logger
        save: _TxHandler

        async def run(self) -> None:
            pass

    logger = port_stub(Logger)()
    uc = Simple(logger=logger, save=handler)
    with pytest.raises(RuntimeError):
        await uc.run()
    assert session._rolled_back


async def test_use_case_can_emit_events_directly() -> None:
    class EmittingUseCase(UseCase):
        async def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="from_uc"))

    uc = EmittingUseCase()
    await uc.run()
    assert len(uc.events) == 1
    assert uc.events[0].name == "from_uc"


async def test_post_init_runs_on_use_case() -> None:
    called: list[bool] = []

    class WithPostInit(UseCase):
        def __post_init__(self) -> None:
            called.append(True)

        async def run(self) -> None:
            pass

    WithPostInit()
    assert called == [True]


async def test_mixed_all_sync_ports_on_success() -> None:
    session = _TxSyncSession()
    handler = _TxSyncSessionHandler(session=session)

    class Simple(UseCase):
        __skip_port_check__ = True
        logger: Logger
        event_bus: EventBus
        save: _TxSyncSessionHandler

        async def run(self) -> None:
            pass

    logger = port_stub(Logger)()
    bus = port_stub(EventBus)()
    uc = Simple(logger=logger, event_bus=bus, save=handler)
    await uc.run()
    assert session._committed
    assert not session._rolled_back
    completions = [c for c in logger.info.call_args_list if "completed" in str(c.args[0])]
    assert len(completions) == 1


async def test_mixed_all_sync_ports_on_failure() -> None:
    session = _TxSyncSession()
    handler = _TxSyncSessionHandler(session=session)

    class Fail(UseCase):
        __skip_port_check__ = True
        logger: Logger
        save: _TxSyncSessionHandler

        async def run(self) -> None:
            raise ValueError("oops")

    logger = port_stub(Logger)()
    uc = Fail(logger=logger, save=handler)
    with pytest.raises(ValueError):
        await uc.run()
    assert session._rolled_back
    assert not session._committed
    assert any("failed" in str(e) for e in [str(c.args[0]) for c in logger.error.call_args_list])


async def test_mixed_sync_session_async_event_bus() -> None:
    session = _TxSyncSession()
    handler = _TxSyncSessionHandler(session=session)

    class Emit(UseCase):
        __skip_port_check__ = True
        event_bus: AsyncEventBus
        save: _TxSyncSessionHandler

        async def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="test"))

    bus = port_stub(AsyncEventBus)()
    uc = Emit(event_bus=bus, save=handler)
    await uc.run()
    assert session._committed
    assert bus.publish.call_count == 1


async def test_async_use_case_returns_run_value() -> None:
    class SumUC(UseCase):
        async def run(self, a: int, b: int) -> int:
            return a + b

    uc = SumUC()
    result = await uc.run(3, 4)
    assert result == 7


async def test_async_use_case_returns_none() -> None:
    class NoOp(UseCase):
        async def run(self) -> None:
            pass

    uc = NoOp()
    result = await uc.run()
    assert result is None


async def test_async_use_case_returns_complex_value() -> None:
    class GetUser(UseCase):
        async def run(self, name: str) -> dict[str, str]:
            return {"name": name, "id": "1"}

    uc = GetUser()
    result = await uc.run("Alice")
    assert result == {"name": "Alice", "id": "1"}


async def test_tx_picks_up_handler_session_on_run() -> None:
    session = _TxSyncSession()
    handler = _SaveHandler(session=session)
    uc = _MyUC(save=handler)
    await uc.run()
    assert session._committed


async def test_keyboard_interrupt_propagates_through_async_use_case() -> None:
    class Interrupting(UseCase):
        async def run(self) -> None:
            raise KeyboardInterrupt()

    uc = Interrupting()
    with pytest.raises(KeyboardInterrupt):
        await uc.run()


async def test_system_exit_propagates_through_async_use_case() -> None:
    class Exiting(UseCase):
        async def run(self) -> None:
            raise SystemExit(1)

    uc = Exiting()
    with pytest.raises(SystemExit):
        await uc.run()
