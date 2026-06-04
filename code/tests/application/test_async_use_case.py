from __future__ import annotations

import pytest
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.core.event_emitter import Event
from aod._internal.domain import RootEntity, ValueObject
from aod.application.use_case.async_ import UseCase as AsyncUseCase
from tests.application.test_async_port import AsyncSpyUnitOfWork
from tests.doubles import SpyEventBus, SpyLogger


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


class CreateUser(AsyncUseCase):
    user_id: int
    name: str

    async def run(self) -> None:
        user = User(id=self.user_id, name=self.name)
        user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))


async def test_async_use_case_is_abstract() -> None:
    with pytest.raises(TypeError):
        AsyncUseCase()


async def test_subclass_without_run_is_abstract() -> None:
    class Incomplete(AsyncUseCase):
        pass

    with pytest.raises(TypeError):
        Incomplete()


async def test_subclass_with_run_can_be_instantiated() -> None:
    CreateUser(user_id=1, name="Alice")


async def test_events_is_empty_before_run() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    assert uc.events == []


async def test_events_is_empty_after_init_even_without_call() -> None:
    class NoOp(AsyncUseCase):
        async def run(self) -> None:
            pass

    uc = NoOp()
    assert uc.events == []


async def test_run_collects_events_from_entity() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    await uc.run()
    assert len(uc.events) == 1
    assert isinstance(uc.events[0], UserCreated)
    assert uc.events[0].user_id == 1
    assert uc.events[0].name == "Alice"


async def test_run_collects_multiple_events_from_entity() -> None:
    class MultiEmit(AsyncUseCase):
        user_id: int

        async def run(self) -> None:
            user = User(id=self.user_id, name="Alice")
            user.rename("Bob")
            user.rename("Charlie")

    uc = MultiEmit(user_id=1)
    await uc.run()
    assert len(uc.events) == 2
    assert all(isinstance(e, UserRenamed) for e in uc.events)
    assert uc.events[0].new_name == "Bob"
    assert uc.events[1].new_name == "Charlie"


async def test_run_replaces_previous_events() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    await uc.run()
    assert len(uc.events) == 1
    await uc.run()
    assert len(uc.events) == 1


async def test_run_with_no_events_keeps_empty_list() -> None:
    class NoOp(AsyncUseCase):
        async def run(self) -> None:
            pass

    uc = NoOp()
    await uc.run()
    assert uc.events == []


async def test_run_takes_no_parameters() -> None:
    captured: list[int] = []

    class Stateful(AsyncUseCase):
        value: int

        async def run(self) -> None:
            captured.append(self.value)

    uc = Stateful(value=42)
    await uc.run()
    assert captured == [42]


async def test_subclass_can_have_private_methods() -> None:
    class WithHelper(AsyncUseCase):
        user_id: int

        async def _double(self, n: int) -> int:
            return n * 2

        async def run(self) -> None:
            assert await self._double(self.user_id) == 4

    await WithHelper(user_id=2).run()


async def test_subclass_with_complex_init_state() -> None:
    class Complex(AsyncUseCase):
        user_id: int
        address: Address

        async def run(self) -> None:
            user = User(id=self.user_id, name="Alice", address=self.address)
            user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))

    addr = Address(street="Main St", city="Springfield")
    uc = Complex(user_id=1, address=addr)
    await uc.run()
    assert len(uc.events) == 1


async def test_run_is_wrapped_automatically() -> None:
    class MyUseCase(AsyncUseCase):
        called: bool = False

        async def run(self) -> None:
            self.called = True

    uc = MyUseCase()
    assert uc.called is False
    await uc.run()
    assert uc.called is True


async def test_events_is_immutable_from_outside() -> None:
    uc = CreateUser(user_id=1, name="Alice")
    await uc.run()
    assert len(uc.events) == 1
    with pytest.raises(MutationForbiddenException):
        uc.events.append(UserCreated(user_id=2, name="Bob"))
    with pytest.raises(MutationForbiddenException):
        uc.events = []


async def test_run_exception_still_collects_emitted_events() -> None:
    class FailAfterEmit(AsyncUseCase):
        user_id: int

        async def run(self) -> None:
            user = User(id=self.user_id, name="Alice")
            user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))
            msg = "boom"
            raise ValueError(msg)

    uc = FailAfterEmit(user_id=1)
    with pytest.raises(ValueError, match="boom"):
        await uc.run()
    assert len(uc.events) == 1


async def test_run_exception_no_emit_keeps_events_empty() -> None:
    class FailFast(AsyncUseCase):
        async def run(self) -> None:
            msg = "fail"
            raise ValueError(msg)

    uc = FailFast()
    with pytest.raises(ValueError, match="fail"):
        await uc.run()
    assert uc.events == []


async def test_events_not_shared_across_instances() -> None:
    uc1 = CreateUser(user_id=1, name="Alice")
    uc2 = CreateUser(user_id=2, name="Bob")
    await uc1.run()
    assert len(uc1.events) == 1
    assert uc2.events == []


async def test_uow_auto_commit_on_success() -> None:
    class Create(AsyncUseCase):
        async def run(self) -> None:
            pass

    uow = AsyncSpyUnitOfWork()
    uc = Create(uow=uow)
    await uc.run()
    assert uow.committed
    assert not uow.rolled_back


async def test_uow_auto_rollback_on_failure() -> None:
    class Fail(AsyncUseCase):
        async def run(self) -> None:
            raise ValueError("oops")

    uow = AsyncSpyUnitOfWork()
    uc = Fail(uow=uow)
    with pytest.raises(ValueError):
        await uc.run()
    assert uow.rolled_back
    assert not uow.committed


async def test_logger_auto_logs_completion() -> None:
    class Simple(AsyncUseCase):
        async def run(self) -> None:
            pass

    logger = SpyLogger()
    uc = Simple(logger=logger)
    await uc.run()
    completions = [e for e in logger.entries if "completed" in str(e.msg)]
    assert len(completions) == 1


async def test_event_bus_auto_publishes_on_success() -> None:
    class Emit(AsyncUseCase):
        async def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="test"))

    bus = SpyEventBus()
    uc = Emit(event_bus=bus)
    await uc.run()
    assert len(bus.published) == 1


async def test_commit_failure_rolls_back_and_logs() -> None:
    class FailingUoW(AsyncSpyUnitOfWork):
        async def commit(self) -> None:
            raise RuntimeError("commit failed")

    class Simple(AsyncUseCase):
        async def run(self) -> None:
            pass

    uow = FailingUoW()
    logger = SpyLogger()
    uc = Simple(uow=uow, logger=logger)
    with pytest.raises(RuntimeError):
        await uc.run()
    assert uow.rolled_back
    assert not uow.committed


async def test_use_case_can_emit_events_directly() -> None:
    class EmittingUseCase(AsyncUseCase):
        async def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="from_uc"))

    uc = EmittingUseCase()
    await uc.run()
    assert len(uc.events) == 1
    assert uc.events[0].name == "from_uc"


async def test_post_init_runs_on_use_case() -> None:
    called: list[bool] = []

    class WithPostInit(AsyncUseCase):
        user_id: int

        def __post_init__(self) -> None:
            called.append(True)

        async def run(self) -> None:
            pass

    WithPostInit(user_id=1)
    assert called == [True]
