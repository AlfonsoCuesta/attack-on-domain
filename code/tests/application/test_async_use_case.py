from __future__ import annotations

import pytest
from aod._internal.application.event_bus import AsyncEventBus, EventBus
from aod._internal.application.logger import AsyncLogger, Logger
from aod._internal.application.unit_of_work import AsyncUnitOfWork, UnitOfWork
from aod._internal.application.use_case import AsyncUseCase as UseCase
from aod._internal.core.domain_exception import MutationForbiddenException
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


async def test_uow_auto_commit_on_success() -> None:
    class Create(UseCase):
        async def run(self) -> None:
            pass

    uow = port_stub(AsyncUnitOfWork)()
    uc = Create()
    object.__setattr__(uc, "_uow", uow)
    await uc.run()
    assert uow.commit.called
    assert not uow.rollback.called


async def test_uow_always_commits_on_success() -> None:
    class NoOp(UseCase):
        async def run(self) -> None:
            pass

    uow = port_stub(AsyncUnitOfWork)()
    uc = NoOp()
    object.__setattr__(uc, "_uow", uow)
    await uc.run()
    assert uow.commit.called
    assert not uow.rollback.called


async def test_uow_auto_rollback_on_failure() -> None:
    class Fail(UseCase):
        async def run(self) -> None:
            raise ValueError("oops")

    uow = port_stub(AsyncUnitOfWork)()
    uc = Fail()
    object.__setattr__(uc, "_uow", uow)
    with pytest.raises(ValueError):
        await uc.run()
    assert uow.rollback.called
    assert not uow.commit.called


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
    class Simple(UseCase):
        logger: Logger

        async def run(self) -> None:
            pass

    uow = port_stub(AsyncUnitOfWork)()
    uow.commit.side_effect = RuntimeError("commit failed")
    logger = port_stub(Logger)()
    uc = Simple(logger=logger)
    object.__setattr__(uc, "_uow", uow)
    with pytest.raises(RuntimeError):
        await uc.run()
    assert uow.rollback.called


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
    class Simple(UseCase):
        logger: Logger
        event_bus: EventBus

        async def run(self) -> None:
            pass

    uow = port_stub(UnitOfWork)()
    logger = port_stub(Logger)()
    bus = port_stub(EventBus)()
    uc = Simple(logger=logger, event_bus=bus)
    object.__setattr__(uc, "_uow", uow)
    await uc.run()
    assert uow.commit.called
    assert not uow.rollback.called
    completions = [c for c in logger.info.call_args_list if "completed" in str(c.args[0])]
    assert len(completions) == 1


async def test_mixed_all_sync_ports_on_failure() -> None:
    class Fail(UseCase):
        logger: Logger

        async def run(self) -> None:
            raise ValueError("oops")

    uow = port_stub(UnitOfWork)()
    logger = port_stub(Logger)()
    uc = Fail(logger=logger)
    object.__setattr__(uc, "_uow", uow)
    with pytest.raises(ValueError):
        await uc.run()
    assert uow.rollback.called
    assert not uow.commit.called
    assert any("failed" in str(e) for e in [str(c.args[0]) for c in logger.error.call_args_list])


async def test_mixed_sync_uow_async_event_bus() -> None:
    class Emit(UseCase):
        event_bus: AsyncEventBus

        async def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="test"))

    uow = port_stub(UnitOfWork)()
    bus = port_stub(AsyncEventBus)()
    uc = Emit(event_bus=bus)
    object.__setattr__(uc, "_uow", uow)
    await uc.run()
    assert uow.commit.called
    assert bus.publish.call_count == 1


async def test_mixed_async_uow_sync_logger() -> None:
    class Simple(UseCase):
        logger: Logger

        async def run(self) -> None:
            pass

    uow = port_stub(AsyncUnitOfWork)()
    logger = port_stub(Logger)()
    uc = Simple(logger=logger)
    object.__setattr__(uc, "_uow", uow)
    await uc.run()
    assert uow.commit.called
    assert not uow.rollback.called
    completions = [c for c in logger.info.call_args_list if "completed" in str(c.args[0])]
    assert len(completions) == 1


async def test_mixed_sync_event_bus_async_logger() -> None:
    class Emit(UseCase):
        event_bus: EventBus
        logger: AsyncLogger

        async def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="test"))

    bus = port_stub(EventBus)()
    logger = port_stub(AsyncLogger)()
    uc = Emit(event_bus=bus, logger=logger)
    await uc.run()
    assert bus.publish.call_count == 1
    completions = [c for c in logger.info.call_args_list if "completed" in str(c.args[0])]
    assert len(completions) == 1


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
