from __future__ import annotations

from abc import abstractmethod

import pytest
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.core.event_emitter import Event, EventCollector
from aod._internal.core.fields.fields import PrivateField
from aod._internal.domain import RootEntity, ValueObject
from aod.application import UseCase
from tests.doubles import SpyEventBus, SpyLogger, SpyUnitOfWork


class UserCreated(Event):
    user_id: int
    name: str


class UserRenamed(Event):
    user_id: int
    new_name: str


class Address(ValueObject):
    street: str
    city: str


class User(RootEntity):
    id: int
    name: str
    address: Address | None = None

    def rename(self, new_name: str) -> None:
        self.name = new_name
        self._event_emitter.emit(UserRenamed(user_id=self.id, new_name=new_name))


class CreateUser(UseCase):
    user_id: int
    name: str

    def run(self) -> None:
        user = User(id=self.user_id, name=self.name)
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
    CreateUser(user_id=1, name="Alice")


def test_events_is_empty_before_run() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    assert uc.events == []


def test_events_is_empty_after_init_even_without_call() -> None:
    class NoOp(UseCase):
        def run(self) -> None:
            pass

    uc = NoOp()
    assert uc.events == []


def test_run_collects_events_from_entity() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    uc.run()
    assert len(uc.events) == 1
    assert isinstance(uc.events[0], UserCreated)
    assert uc.events[0].user_id == 1
    assert uc.events[0].name == "Alice"


def test_run_collects_multiple_events_from_entity() -> None:
    class MultiEmit(UseCase):
        user_id: int

        def run(self) -> None:
            user = User(id=self.user_id, name="Alice")
            user.rename("Bob")
            user.rename("Charlie")

    uc = MultiEmit(user_id=1)
    uc.run()
    assert len(uc.events) == 2
    assert all(isinstance(e, UserRenamed) for e in uc.events)
    assert uc.events[0].new_name == "Bob"
    assert uc.events[1].new_name == "Charlie"


def test_run_replaces_previous_events() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    uc.run()
    assert len(uc.events) == 1
    uc.run()
    assert len(uc.events) == 1


def test_run_with_no_events_keeps_empty_list() -> None:
    class NoOp(UseCase):
        def run(self) -> None:
            pass

    uc = NoOp()
    uc.run()
    assert uc.events == []


def test_run_takes_no_parameters() -> None:
    captured: list[int] = []

    class Stateful(UseCase):
        value: int

        def run(self) -> None:
            captured.append(self.value)

    uc = Stateful(value=42)
    uc.run()
    assert captured == [42]


def test_subclass_can_have_private_methods() -> None:
    class WithHelper(UseCase):
        user_id: int

        def _double(self, n: int) -> int:
            return n * 2

        def run(self) -> None:
            assert self._double(self.user_id) == 4

    WithHelper(user_id=2).run()


def test_subclass_with_complex_init_state() -> None:
    class Complex(UseCase):
        user_id: int
        address: Address

        def run(self) -> None:
            user = User(id=self.user_id, name="Alice", address=self.address)
            user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))

    addr = Address(street="Main St", city="Springfield")
    uc = Complex(user_id=1, address=addr)
    uc.run()
    assert len(uc.events) == 1


def test_run_is_wrapped_automatically() -> None:
    class MyUseCase(UseCase):
        called: bool = False

        def run(self) -> None:
            self.called = True

    uc = MyUseCase()
    assert uc.called is False
    uc.run()
    assert uc.called is True


def test_events_is_immutable_from_outside() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    uc.run()
    assert len(uc.events) == 1
    with pytest.raises(MutationForbiddenException):
        uc.events.append(UserCreated(user_id=2, name="Bob"))
    with pytest.raises(MutationForbiddenException):
        uc.events = []


def test_events_is_iterable() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    uc.run()
    events_list = [e for e in uc.events]
    assert len(events_list) == 1


def test_events_supports_indexing() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    uc.run()
    assert isinstance(uc.events[0], UserCreated)


def test_events_supports_slicing() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    uc.run()
    sliced = uc.events[0:1]
    assert len(sliced) == 1
    assert isinstance(sliced[0], UserCreated)


def test_run_exception_still_collects_emitted_events() -> None:
    class FailAfterEmit(UseCase):
        user_id: int

        def run(self) -> None:
            user = User(id=self.user_id, name="Alice")
            user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))
            msg = "boom"
            raise ValueError(msg)

    uc = FailAfterEmit(user_id=1)
    with pytest.raises(ValueError, match="boom"):
        uc.run()
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
    uc1 = CreateUser(user_id=1, name="Alice")
    uc2 = CreateUser(user_id=2, name="Bob")
    uc1.run()
    assert len(uc1.events) == 1
    assert uc2.events == []


def test_events_independent_after_separate_runs() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    uc.run()
    first_events = list(uc.events)
    uc.run()
    assert len(first_events) == 1
    assert len(uc.events) == 1


def test_repr_includes_fields() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    rep = repr(uc)
    assert "CreateUser" in rep
    assert "user_id=1" in rep
    assert "name=" in rep


def test_repr_includes_events() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    uc.run()
    rep = repr(uc)
    assert "events=" in rep


def test_post_init_runs_on_use_case() -> None:
    called: list[bool] = []

    class WithPostInit(UseCase):
        user_id: int

        def __post_init__(self) -> None:
            called.append(True)

        def run(self) -> None:
            pass

    WithPostInit(user_id=1)
    assert called == [True]


def test_post_init_can_setup_state() -> None:
    class WithPostInit(UseCase):
        user_id: int
        doubled: int = 0

        def __post_init__(self) -> None:
            self.doubled = self.user_id * 2

        def run(self) -> None:
            pass

    uc = WithPostInit(user_id=5)
    assert uc.doubled == 10


def test_post_init_does_not_run_on_use_case_without_override() -> None:
    class Simple(UseCase):
        user_id: int

        def run(self) -> None:
            pass

    uc = Simple(user_id=1)
    assert uc.user_id == 1


def test_inheritance_chain_with_intermediate_abstract() -> None:
    class BaseUseCase(UseCase):
        base_field: str

        @abstractmethod
        def run(self) -> None: ...

    class Concrete(BaseUseCase):
        def run(self) -> None:
            pass

    c = Concrete(base_field="hello")
    c.run()
    assert c.base_field == "hello"


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
        order_id: int

        def run(self) -> None:
            user = User(id=self.order_id, name="order")
            user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))

    class SpecificOrder(BaseOrder):
        pass

    uc = SpecificOrder(order_id=99)
    uc.run()
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
    uc = CreateUser(user_id=1, name="Alice")
    with EventCollector():
        uc.run()
    assert len(uc.events) == 1


def test_re_run_does_not_keep_old_events() -> None:
    uc = CreateUser(user_id=1, name="First")
    uc.run()
    assert len(uc.events) == 1
    uc.run()
    assert len(uc.events) == 1


def test_cannot_set_arbitrary_fields_from_outside() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    with pytest.raises(MutationForbiddenException):
        uc.user_id = 99


def test_cannot_set_arbitrary_fields_after_run() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    uc.run()
    with pytest.raises(MutationForbiddenException):
        uc.user_id = 99


def test_cannot_del_fields() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    with pytest.raises(MutationForbiddenException):
        del uc.user_id


def test_no_public_methods_exposed_besides_run() -> None:
    public = {n for n in dir(CreateUser) if not n.startswith("_")}
    assert "run" in public


def test_double_wrapping_does_not_break() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    uc.run()
    uc.run()
    assert len(uc.events) == 1


def test_many_runs() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    for _ in range(10):
        uc.run()
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

    uow = SpyUnitOfWork()
    uc = Create(uow=uow)
    uc.run()
    assert uow.committed
    assert not uow.rolled_back


def test_uow_auto_rollback_on_failure() -> None:
    class Fail(UseCase):
        def run(self) -> None:
            raise ValueError("oops")

    uow = SpyUnitOfWork()
    uc = Fail(uow=uow)
    with pytest.raises(ValueError):
        uc.run()
    assert uow.rolled_back
    assert not uow.committed


def test_logger_auto_logs_completion() -> None:
    class Simple(UseCase):
        def run(self) -> None:
            pass

    logger = SpyLogger()
    uc = Simple(logger=logger)
    uc.run()
    completions = [e for e in logger.entries if "completed" in str(e.msg)]
    assert len(completions) == 1


def test_logger_auto_logs_events_count() -> None:
    class Emit(UseCase):
        def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="test"))

    logger = SpyLogger()
    uc = Emit(logger=logger)
    uc.run()
    completions = [e for e in logger.entries if "completed" in str(e.msg)]
    assert len(completions) == 1
    assert completions[0].context.get("events") == 1


def test_logger_auto_logs_failure() -> None:
    class Fail(UseCase):
        def run(self) -> None:
            raise ValueError("oops")

    logger = SpyLogger()
    uc = Fail(logger=logger)
    with pytest.raises(ValueError):
        uc.run()
    errors = [e for e in logger.entries if e.level == "error"]
    assert len(errors) >= 1
    assert "failed" in str(errors[0].msg)


def test_event_bus_auto_publishes_on_success() -> None:
    class Emit(UseCase):
        def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="test"))

    bus = SpyEventBus()
    uc = Emit(event_bus=bus)
    uc.run()
    assert len(bus.published) == 1


def test_commit_failure_rolls_back_and_logs() -> None:
    class FailingUoW(SpyUnitOfWork):
        def commit(self) -> None:
            raise RuntimeError("commit failed")

    class Simple(UseCase):
        def run(self) -> None:
            pass

    uow = FailingUoW()
    logger = SpyLogger()
    uc = Simple(uow=uow, logger=logger)
    with pytest.raises(RuntimeError):
        uc.run()
    assert uow.rolled_back
    assert not uow.committed
    errors = [e for e in logger.entries if e.level == "error"]
    assert any("commit failed" in str(e.msg) for e in errors)
