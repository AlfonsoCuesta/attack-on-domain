from __future__ import annotations

import pytest

from aod._internal.application.use_case import UseCase
from aod._internal.core.event_emitter import Event
from aod._internal.domain import RootEntity, ValueObject


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
    from aod._internal.core.domain_exception import MutationForbiddenException

    uc = CreateUser(user_id=1, name="Alice")
    uc.run()
    assert len(uc.events) == 1
    with pytest.raises(MutationForbiddenException):
        uc.events.append(UserCreated(user_id=2, name="Bob"))
    with pytest.raises(MutationForbiddenException):
        uc.events = []
