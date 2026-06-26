import pytest
from aod._internal.core.base_validator import BaseValidator
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.core.event_emitter import Event, EventCollector
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.entity_id import EntityId
from aod._internal.domain.value_object import ValueObject
from aod.domain import Field


class IntId(EntityId):
    value: int


# ---------------------------------------------------------------------------
# __post_init__ is defined on BaseValidator (for MRO support) but only
# triggered from BaseGuarded.__init__, so it works on Entity, RootEntity,
# ValueObject, and any BaseGuarded subclass.
# ---------------------------------------------------------------------------


def test_post_init_exists_on_base() -> None:
    assert hasattr(BaseValidator, "__post_init__")


# ---------------------------------------------------------------------------
# Entity — __post_init__
# ---------------------------------------------------------------------------


def test_entity_post_init_runs_on_normal_construction() -> None:
    called: list[bool] = []

    class User(Entity):
        id: IntId = Field(id=True)

        def __post_init__(self) -> None:
            called.append(True)

    User(id=IntId(value=1))

    assert called == [True]


def test_entity_post_init_does_not_run_on_reconstruct() -> None:
    called: list[bool] = []

    class User(Entity):
        id: IntId = Field(id=True)

        def __post_init__(self) -> None:
            called.append(True)

    User.reconstruct(id=IntId(value=1))

    assert called == []


def test_entity_post_init_can_emit_events() -> None:
    class UserCreated(Event):
        user_id: int

    class User(Entity):
        id: IntId = Field(id=True)

        def __post_init__(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=self.id.value))

    user = User(id=IntId(value=42))

    events = user._event_emitter.poll_events()
    assert len(events) == 1
    assert isinstance(events[0], UserCreated)
    assert events[0].user_id == 42


def test_entity_post_init_does_not_emit_on_reconstruct() -> None:
    class UserCreated(Event):
        user_id: int

    class User(Entity):
        id: IntId = Field(id=True)

        def __post_init__(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=self.id.value))

    user = User.reconstruct(id=IntId(value=42))

    assert user._event_emitter.poll_events() == []


def test_entity_post_init_events_collected_by_event_collector() -> None:
    class UserCreated(Event):
        user_id: int

    class User(Entity):
        id: IntId = Field(id=True)

        def __post_init__(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=self.id.value))

    with EventCollector() as collected:
        User(id=IntId(value=1))

    assert len(collected) == 1
    assert isinstance(collected[0], UserCreated)
    assert collected[0].user_id == 1


def test_entity_post_init_can_call_public_methods() -> None:
    class User(Entity):
        id: IntId = Field(id=True)

        called: list[bool] = []

        def __post_init__(self) -> None:
            self.setup()

        def setup(self) -> None:
            self.called.append(True)

    user = User(id=IntId(value=1))

    assert user.called == [True]


def test_entity_post_init_can_set_fields() -> None:
    class User(Entity):
        id: IntId = Field(id=True)
        label: str = ""

        def __post_init__(self) -> None:
            object.__setattr__(self, "label", f"user:{self.id.value}")

    user = User(id=IntId(value=7))

    assert user.label == "user:7"


def test_entity_post_init_not_called_on_reconstruct_with_custom_init() -> None:
    post_init_ran: list[bool] = []

    class User(Entity):
        id: IntId = Field(id=True)

        def __post_init__(self) -> None:
            post_init_ran.append(True)

    User(id=IntId(value=1))
    User.reconstruct(id=IntId(value=2))

    assert post_init_ran == [True]


# ---------------------------------------------------------------------------
# RootEntity — __post_init__
# ---------------------------------------------------------------------------


def test_root_entity_post_init_runs_on_normal_construction() -> None:
    called: list[bool] = []

    class Aggregate(RootEntity):
        id: IntId = Field(id=True)

        def __post_init__(self) -> None:
            called.append(True)

    Aggregate(id=IntId(value=1))

    assert called == [True]


def test_root_entity_post_init_emits_events() -> None:
    class AggregateCreated(Event):
        aggregate_id: int

    class Aggregate(RootEntity):
        id: IntId = Field(id=True)

        def __post_init__(self) -> None:
            self._event_emitter.emit(AggregateCreated(aggregate_id=self.id.value))

    agg = Aggregate(id=IntId(value=99))

    events = agg._event_emitter.poll_events()
    assert len(events) == 1
    assert isinstance(events[0], AggregateCreated)
    assert events[0].aggregate_id == 99


# ---------------------------------------------------------------------------
# ValueObject — __post_init__
# ---------------------------------------------------------------------------


def test_value_object_post_init_runs_on_normal_construction() -> None:
    called: list[bool] = []

    class Money(ValueObject):
        amount: int

        def __post_init__(self) -> None:
            called.append(True)

    Money(amount=100)

    assert called == [True]


def test_value_object_post_init_does_not_run_on_reconstruct() -> None:
    called: list[bool] = []

    class Money(ValueObject):
        amount: int

        def __post_init__(self) -> None:
            called.append(True)

    Money.reconstruct(amount=100)

    assert called == []


def test_value_object_post_init_can_emit_events() -> None:
    class MoneyCreated(Event):
        amount: int

    class Money(ValueObject):
        amount: int

        def __post_init__(self) -> None:
            self._event_emitter.emit(MoneyCreated(amount=self.amount))

    money = Money(amount=50)

    events = money._event_emitter.poll_events()
    assert len(events) == 1
    assert isinstance(events[0], MoneyCreated)
    assert events[0].amount == 50


def test_value_object_post_init_does_not_emit_on_reconstruct() -> None:
    class MoneyCreated(Event):
        amount: int

    class Money(ValueObject):
        amount: int

        def __post_init__(self) -> None:
            self._event_emitter.emit(MoneyCreated(amount=self.amount))

    money = Money.reconstruct(amount=50)

    assert money._event_emitter.poll_events() == []


def test_value_object_post_init_can_call_public_methods() -> None:
    class Money(ValueObject):
        amount: int

        called: list[bool] = []

        def __post_init__(self) -> None:
            self.normalize()

        def normalize(self) -> None:
            self.called.append(True)

    m = Money(amount=100)

    assert m.called == [True]


def test_value_object_post_init_can_set_fields() -> None:
    class Money(ValueObject):
        amount: int
        currency: str = "USD"

        def __post_init__(self) -> None:
            object.__setattr__(self, "currency", "EUR")

    money = Money(amount=100)

    assert money.currency == "EUR"


def test_value_object_still_immutable_after_post_init() -> None:
    class Money(ValueObject):
        amount: int

        def __post_init__(self) -> None:
            object.__setattr__(self, "currency", "EUR")

    money = Money(amount=100)

    with pytest.raises(MutationForbiddenException, match="Cannot mutate this object"):
        money.amount = 200


# ---------------------------------------------------------------------------
# Inheritance — __post_init__ via super().__post_init__()
# ---------------------------------------------------------------------------


def test_post_init_calls_super_in_entity_inheritance() -> None:
    called: list[str] = []

    class BaseEntity(Entity):
        id: IntId = Field(id=True)
        x: int

        def __post_init__(self) -> None:
            called.append("base")

    class ChildEntity(BaseEntity):
        id: IntId = Field(id=True)
        y: int

        def __post_init__(self) -> None:
            super().__post_init__()
            called.append("child")

    ChildEntity(id=IntId(value=1), x=1, y=2)

    assert called == ["base", "child"]


def test_post_init_inherits_from_entity_parent() -> None:
    called: list[str] = []

    class BaseEntity(Entity):
        id: IntId = Field(id=True)
        x: int

        def __post_init__(self) -> None:
            called.append("base")

    class ChildEntity(BaseEntity):
        id: IntId = Field(id=True)
        y: int

    ChildEntity(id=IntId(value=1), x=1, y=2)

    assert called == ["base"]


def test_post_init_not_called_on_reconstruct_with_inheritance() -> None:
    called: list[str] = []

    class BaseEntity(Entity):
        id: IntId = Field(id=True)
        x: int

        def __post_init__(self) -> None:
            called.append("base")

    class ChildEntity(BaseEntity):
        id: IntId = Field(id=True)
        y: int

        def __post_init__(self) -> None:
            super().__post_init__()
            called.append("child")

    ChildEntity.reconstruct(id=IntId(value=1), x=1, y=2)

    assert called == []


# ---------------------------------------------------------------------------
# Mixed — multiple domain objects with __post_init__
# ---------------------------------------------------------------------------


def test_multiple_entities_each_emit_own_events_via_post_init() -> None:
    class UserCreated(Event):
        user_id: int

    class OrderCreated(Event):
        order_id: int

    class User(RootEntity):
        id: IntId = Field(id=True)

        def __post_init__(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=self.id.value))

    class Order(RootEntity):
        id: IntId = Field(id=True)

        def __post_init__(self) -> None:
            self._event_emitter.emit(OrderCreated(order_id=self.id.value))

    with EventCollector() as collected:
        user = User(id=IntId(value=1))
        order = Order(id=IntId(value=2))

    assert len(collected) == 2
    assert collected[0].user_id == 1
    assert collected[1].order_id == 2
    assert user._event_emitter.poll_events() == [collected[0]]
    assert order._event_emitter.poll_events() == [collected[1]]
