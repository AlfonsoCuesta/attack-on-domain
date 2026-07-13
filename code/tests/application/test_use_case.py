from __future__ import annotations

from abc import abstractmethod

import pytest
from aod._internal.application.event_bus import EventBus
from aod._internal.application.logger import Logger
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.core.event_emitter import EventCollector
from aod._internal.core.fields.fields import PrivateField
from aod._internal.application.unit_of_work import UnitOfWork
from aod.application import UseCase
from aod.testing.doubles import port_stub
from tests.application._use_case_scenarios import (
    _RUN_BODIES,
    SCENARIOS,
    Address,
    Scenario,
    User,
    UserCreated,
    UserRenamed,
)


class CreateUser(UseCase):
    def run(self, user_id: int, name: str) -> None:
        user = User(id=user_id, name=name)
        user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))


def test_use_case_is_abstract() -> None:
    with pytest.raises(TypeError):
        UseCase()


def test_subclass_without_run_is_abstract() -> None:
    class Incomplete(UseCase):
        pass

    with pytest.raises(TypeError):
        Incomplete()


def test_subclass_with_run_can_be_instantiated() -> None:
    CreateUser()


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_scenario(scenario: Scenario) -> None:
    body = _RUN_BODIES[scenario.name]
    ns = {
        "run": lambda self, *args, **kwargs: body(self, *args, **kwargs),
    }
    cls = type(scenario.name, (UseCase,), ns)
    uc = cls()
    if scenario.expected_exception is not None:
        with pytest.raises(scenario.expected_exception):
            uc.run(**scenario.kwargs)
    else:
        uc.run(**scenario.kwargs)
    assert len(uc.events) == scenario.expected_events


def test_events_is_empty_before_run() -> None:
    uc = CreateUser()
    assert uc.events == []


def test_events_is_empty_after_init_even_without_call() -> None:
    class NoOp(UseCase):
        def run(self) -> None:
            pass

    uc = NoOp()
    assert uc.events == []


def test_run_collects_events_from_entity() -> None:
    uc = CreateUser()
    uc.run(user_id=1, name="Alice")
    assert len(uc.events) == 1
    assert isinstance(uc.events[0], UserCreated)
    assert uc.events[0].user_id == 1
    assert uc.events[0].name == "Alice"


def test_run_collects_multiple_events_from_entity() -> None:
    class MultiEmit(UseCase):
        def run(self, user_id: int) -> None:
            user = User(id=user_id, name="Alice")
            user.rename("Bob")
            user.rename("Charlie")

    uc = MultiEmit()
    uc.run(user_id=1)
    assert len(uc.events) == 2
    assert all(isinstance(e, UserRenamed) for e in uc.events)
    assert uc.events[0].new_name == "Bob"
    assert uc.events[1].new_name == "Charlie"


def test_run_replaces_previous_events() -> None:
    uc = CreateUser()
    uc.run(user_id=1, name="Alice")
    assert len(uc.events) == 1
    uc.run(user_id=2, name="Bob")
    assert len(uc.events) == 1


def test_run_with_no_events_keeps_empty_list() -> None:
    class NoOp(UseCase):
        def run(self) -> None:
            pass

    uc = NoOp()
    uc.run()
    assert uc.events == []


def test_run_takes_parameters() -> None:
    captured: list[int] = []

    class Stateful(UseCase):
        def run(self, value: int) -> None:
            captured.append(value)

    uc = Stateful()
    uc.run(value=42)
    assert captured == [42]


def test_subclass_can_have_private_methods() -> None:
    class WithHelper(UseCase):
        def _double(self, n: int) -> int:
            return n * 2

        def run(self, user_id: int) -> None:
            assert self._double(user_id) == 4

    WithHelper().run(user_id=2)


def test_subclass_with_complex_init_state() -> None:
    class Complex(UseCase):
        def run(self, user_id: int, address: Address) -> None:
            user = User(id=user_id, name="Alice", address=address)
            user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))

    addr = Address(street="Main St", city="Springfield")
    uc = Complex()
    uc.run(user_id=1, address=addr)
    assert len(uc.events) == 1


def test_run_is_wrapped_automatically() -> None:
    class MyUseCase(UseCase):
        def run(self) -> None:
            pass

    uc = MyUseCase()
    uc.run()


def test_events_is_immutable_from_outside() -> None:
    uc = CreateUser()
    uc.run(user_id=1, name="Alice")
    assert len(uc.events) == 1
    with pytest.raises(MutationForbiddenException):
        uc.events.append(UserCreated(user_id=2, name="Bob"))
    with pytest.raises(MutationForbiddenException):
        uc.events = []


def test_events_is_iterable() -> None:
    uc = CreateUser()
    uc.run(user_id=1, name="Alice")
    events_list = [e for e in uc.events]
    assert len(events_list) == 1


def test_events_supports_indexing() -> None:
    uc = CreateUser()
    uc.run(user_id=1, name="Alice")
    assert isinstance(uc.events[0], UserCreated)


def test_events_supports_slicing() -> None:
    uc = CreateUser()
    uc.run(user_id=1, name="Alice")
    sliced = uc.events[0:1]
    assert len(sliced) == 1
    assert isinstance(sliced[0], UserCreated)


def test_run_exception_still_collects_emitted_events() -> None:
    class FailAfterEmit(UseCase):
        def run(self, user_id: int) -> None:
            user = User(id=user_id, name="Alice")
            user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))
            msg = "boom"
            raise ValueError(msg)

    uc = FailAfterEmit()
    with pytest.raises(ValueError, match="boom"):
        uc.run(user_id=1)
    assert len(uc.events) == 1


def test_run_exception_no_emit_keeps_events_empty() -> None:
    class FailFast(UseCase):
        def run(self) -> None:
            msg = "fail"
            raise ValueError(msg)

    uc = FailFast()
    with pytest.raises(ValueError, match="fail"):
        uc.run()
    assert uc.events == []


def test_events_not_shared_across_instances() -> None:
    uc1 = CreateUser()
    uc2 = CreateUser()
    uc1.run(user_id=1, name="Alice")
    assert len(uc1.events) == 1
    assert uc2.events == []


def test_events_independent_after_separate_runs() -> None:
    uc = CreateUser()
    uc.run(user_id=1, name="Alice")
    first_events = list(uc.events)
    uc.run(user_id=2, name="Bob")
    assert len(first_events) == 1
    assert len(uc.events) == 1


def test_repr_includes_class_name() -> None:
    uc = CreateUser()
    rep = repr(uc)
    assert "CreateUser" in rep


def test_repr_includes_events() -> None:
    uc = CreateUser()
    uc.run(user_id=1, name="Alice")
    rep = repr(uc)
    assert "events=" in rep


def test_post_init_runs_on_use_case() -> None:
    called: list[bool] = []

    class WithPostInit(UseCase):
        def __post_init__(self) -> None:
            called.append(True)

        def run(self, user_id: int) -> None:
            pass

    WithPostInit()
    assert called == [True]


def test_post_init_can_setup_state() -> None:
    class WithPostInit(UseCase):
        _doubled: int = PrivateField(default=0)

        def __post_init__(self) -> None:
            self._doubled = 10

        def run(self) -> None:
            pass

    uc = WithPostInit()
    assert uc._doubled == 10


def test_post_init_does_not_run_on_use_case_without_override() -> None:
    class Simple(UseCase):
        def run(self) -> None:
            pass

    uc = Simple()
    uc.run()


def test_inheritance_chain_with_intermediate_abstract() -> None:
    class BaseUseCase(UseCase):
        @abstractmethod
        def run(self) -> None: ...

    class Concrete(BaseUseCase):
        def run(self) -> None:
            pass

    c = Concrete()
    c.run()


def test_inheritance_chain_deep() -> None:
    class Level1(UseCase):
        def run(self) -> None:
            pass

    class Level2(Level1):
        def run(self) -> None:
            pass

    class Level3(Level2):
        pass

    l3 = Level3()
    l3.run()


def test_inheritance_chain_preserves_event_collection() -> None:
    class BaseOrder(UseCase):
        def run(self, order_id: int) -> None:
            user = User(id=order_id, name="order")
            user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))

    class SpecificOrder(BaseOrder):
        pass

    uc = SpecificOrder()
    uc.run(order_id=99)
    assert len(uc.events) == 1
    assert uc.events[0].user_id == 99


def test_private_field_on_use_case() -> None:
    class WithPrivate(UseCase):
        _secret: str = PrivateField(default="hidden")

        def run(self) -> None:
            pass

    uc = WithPrivate()
    assert uc._secret == "hidden"


def test_event_collector_already_active_does_not_interfere() -> None:
    uc = CreateUser()
    with EventCollector():
        uc.run(user_id=1, name="Alice")
    assert len(uc.events) == 1


def test_re_run_does_not_keep_old_events() -> None:
    uc = CreateUser()
    uc.run(user_id=1, name="First")
    assert len(uc.events) == 1
    uc.run(user_id=2, name="Second")
    assert len(uc.events) == 1


def test_cannot_set_fields_from_outside() -> None:
    uc = CreateUser()
    with pytest.raises(MutationForbiddenException):
        uc._uow = None  # type: ignore


def test_cannot_del_fields() -> None:
    uc = CreateUser()
    with pytest.raises(MutationForbiddenException):
        del uc._uow


def test_no_public_methods_exposed_besides_run() -> None:
    public = {n for n in dir(CreateUser) if not n.startswith("_")}
    assert "run" in public


def test_double_wrapping_does_not_break() -> None:
    uc = CreateUser()
    uc.run(user_id=1, name="Alice")
    uc.run(user_id=2, name="Bob")
    assert len(uc.events) == 1


def test_many_runs() -> None:
    uc = CreateUser()
    for i in range(10):
        uc.run(user_id=i, name=f"User{i}")
    assert len(uc.events) == 1


def test_use_case_can_emit_events_directly() -> None:
    class EmittingUseCase(UseCase):
        def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="from_uc"))

    uc = EmittingUseCase()
    uc.run()
    assert len(uc.events) == 1
    assert uc.events[0].name == "from_uc"


def test_uow_auto_commit_on_success() -> None:
    class Create(UseCase):
        def run(self) -> None:
            pass

    uow = port_stub(UnitOfWork)()
    uc = Create()
    object.__setattr__(uc, "_uow", uow)
    uc.run()
    assert uow.commit.called
    assert not uow.rollback.called


def test_uow_always_commits_on_success() -> None:
    class NoOp(UseCase):
        def run(self) -> None:
            pass

    uow = port_stub(UnitOfWork)()
    uc = NoOp()
    object.__setattr__(uc, "_uow", uow)
    uc.run()
    assert uow.commit.called
    assert not uow.rollback.called


def test_uow_auto_rollback_on_failure() -> None:
    class Fail(UseCase):
        def run(self) -> None:
            raise ValueError("oops")

    uow = port_stub(UnitOfWork)()
    uc = Fail()
    object.__setattr__(uc, "_uow", uow)
    with pytest.raises(ValueError):
        uc.run()
    assert uow.rollback.called
    assert not uow.commit.called


def test_logger_auto_logs_completion() -> None:
    class Simple(UseCase):
        logger: Logger

        def run(self) -> None:
            pass

    logger = port_stub(Logger)()
    uc = Simple(logger=logger)
    uc.run()
    completions = [c for c in logger.info.call_args_list if "completed" in str(c.args[0])]
    assert len(completions) == 1


def test_logger_auto_logs_events_count() -> None:
    class Emit(UseCase):
        logger: Logger

        def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="test"))

    logger = port_stub(Logger)()
    uc = Emit(logger=logger)
    uc.run()
    completions = [c for c in logger.info.call_args_list if "completed" in str(c.args[0])]
    assert len(completions) == 1
    events_logs = [c for c in logger.info.call_args_list if "events" in str(c.args[0])]
    assert len(events_logs) == 1
    evts = events_logs[0].kwargs.get("events")
    assert evts is not None
    assert len(evts) == 1


def test_logger_auto_logs_failure() -> None:
    class Fail(UseCase):
        logger: Logger

        def run(self) -> None:
            raise ValueError("oops")

    logger = port_stub(Logger)()
    uc = Fail(logger=logger)
    with pytest.raises(ValueError):
        uc.run()
    errors = [c for c in logger.error.call_args_list if "failed" in str(c.args[0])]
    assert len(errors) >= 1


def test_event_bus_auto_publishes_on_success() -> None:
    class Emit(UseCase):
        event_bus: EventBus

        def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="test"))

    bus = port_stub(EventBus)()
    uc = Emit(event_bus=bus)
    uc.run()
    assert bus.publish.call_count == 1


def test_commit_failure_rolls_back_and_logs() -> None:
    class Simple(UseCase):
        logger: Logger

        def run(self) -> None:
            pass

    uow = port_stub(UnitOfWork)()
    uow.commit.side_effect = RuntimeError("commit failed")
    logger = port_stub(Logger)()
    uc = Simple(logger=logger)
    object.__setattr__(uc, "_uow", uow)
    with pytest.raises(RuntimeError):
        uc.run()
    assert uow.rollback.called
    errors = [c for c in logger.error.call_args_list if "commit failed" in str(c.args[0])]
    assert len(errors) >= 1


def test_use_case_returns_run_value() -> None:
    class SumUC(UseCase):
        def run(self, a: int, b: int) -> int:
            return a + b

    uc = SumUC()
    result = uc.run(3, 4)
    assert result == 7


def test_use_case_returns_none() -> None:
    class NoOp(UseCase):
        def run(self) -> None:
            pass

    uc = NoOp()
    result = uc.run()
    assert result is None


def test_use_case_returns_complex_value() -> None:
    class GetUser(UseCase):
        def run(self, name: str) -> dict[str, str]:
            return {"name": name, "id": "1"}

    uc = GetUser()
    result = uc.run("Alice")
    assert result == {"name": "Alice", "id": "1"}
