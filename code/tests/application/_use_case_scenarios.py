from __future__ import annotations

from dataclasses import dataclass, field
from inspect import iscoroutine
from typing import Any

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


async def run_uc(uc: Any) -> None:
    result = uc.run()
    if iscoroutine(result):
        await result


_captured: list[int] = []


def _create_user_body(self: Any) -> None:
    user = User(id=self.user_id, name=self.name)
    user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))


def _multi_emit_body(self: Any) -> None:
    user = User(id=self.user_id, name="Alice")
    user.rename("Bob")
    user.rename("Charlie")


def _fail_after_emit_body(self: Any) -> None:
    user = User(id=self.user_id, name="Alice")
    user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))
    raise ValueError("boom")


def _fail_fast_body(self: Any) -> None:
    raise ValueError("fail")


def _emitting_body(self: Any) -> None:
    self._event_emitter.emit(UserCreated(user_id=1, name="from_uc"))


def _noop_body(self: Any) -> None:
    pass


def _stateful_body(self: Any) -> None:
    _captured.append(self.value)


def _complex_body(self: Any) -> None:
    user = User(id=self.user_id, name="Alice", address=self.address)
    user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))


def _my_uc_body(self: Any) -> None:
    self.called = True


def _with_helper_body(self: Any) -> None:
    assert self._double(self.user_id) == 4


def _with_post_init_body(self: Any) -> None:
    pass


_RUN_BODIES: dict[str, Any] = {
    "CreateUser": _create_user_body,
    "MultiEmit": _multi_emit_body,
    "NoOp": _noop_body,
    "FailAfterEmit": _fail_after_emit_body,
    "FailFast": _fail_fast_body,
    "Stateful": _stateful_body,
    "Complex": _complex_body,
    "MyUseCase": _my_uc_body,
    "WithHelper": _with_helper_body,
    "WithPostInit": _with_post_init_body,
    "EmittingUseCase": _emitting_body,
    "Create": _noop_body,
    "Fail": _fail_fast_body,
    "Simple": _noop_body,
    "Emit": _emitting_body,
    "BaseOrder": _create_user_body,
}


def _make_private_helper(self: Any, n: int) -> int:
    return n * 2


@dataclass
class Scenario:
    name: str
    annotations: dict[str, Any] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)
    kwargs: dict[str, Any] = field(default_factory=dict)
    expected_events: int = 0
    expected_exception: type[BaseException] | None = None


SCENARIOS: list[Scenario] = [
    Scenario(
        name="CreateUser",
        annotations={"user_id": int, "name": str},
        kwargs={"user_id": 1, "name": "Alice"},
        expected_events=1,
    ),
    Scenario(
        name="MultiEmit",
        annotations={"user_id": int},
        kwargs={"user_id": 1},
        expected_events=2,
    ),
    Scenario(
        name="FailAfterEmit",
        annotations={"user_id": int},
        kwargs={"user_id": 1},
        expected_events=1,
        expected_exception=ValueError,
    ),
    Scenario(
        name="FailFast",
        expected_events=0,
        expected_exception=ValueError,
    ),
    Scenario(
        name="EmittingUseCase",
        expected_events=1,
    ),
    Scenario(
        name="NoOp",
        expected_events=0,
    ),
    Scenario(
        name="Stateful",
        annotations={"value": int},
        kwargs={"value": 42},
        expected_events=0,
    ),
    Scenario(
        name="Complex",
        annotations={"user_id": int, "address": Address},
        kwargs={"user_id": 1, "address": Address(street="Main St", city="Springfield")},
        expected_events=1,
    ),
    Scenario(
        name="MyUseCase",
        annotations={"called": bool},
        defaults={"called": False},
        expected_events=0,
    ),
    Scenario(
        name="WithPostInit",
        annotations={"user_id": int},
        kwargs={"user_id": 1},
        expected_events=0,
    ),
]
