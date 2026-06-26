from __future__ import annotations

import pytest
from aod._internal.core.domain_exception import InvarianceException, ModelValidationError
from aod._internal.core.event_emitter import Event
from aod._internal.domain.entity import RootEntity
from aod._internal.domain.entity_id import EntityId
from aod._internal.domain.service import Service
from aod._internal.domain.value_object import ValueObject
from aod.testing import (
    assert_event_emitted,
    assert_no_events,
    build,
    check_invariant,
    events_of,
)
from aod.domain.validation import field_invariance, invariance


class IntId(EntityId):
    value: int


# ── build ────────────────────────────────────────────────────────────────────


class TestBuild:
    def test_entity(self) -> None:
        class User(RootEntity):
            id: IntId
            name: str

        u = build(User, id=IntId(value=1), name="Alf")
        assert isinstance(u, User)
        assert u.id == IntId(value=1)
        assert u.name == "Alf"

    def test_value_object(self) -> None:
        class Coord(ValueObject):
            x: float
            y: float

        c = build(Coord, x=1.0, y=2.0)
        assert isinstance(c, Coord)
        assert c.x == 1.0

    def test_service(self) -> None:
        class MyService(Service):
            pass

        s = build(MyService)
        assert isinstance(s, MyService)

    def test_resets_contextvar(self) -> None:
        class User(RootEntity):
            id: IntId

        u1 = build(User, id=IntId(value=1))
        u2 = build(User, id=IntId(value=2))
        assert u1.id == IntId(value=1)
        assert u2.id == IntId(value=2)

    def test_raises_on_missing_required(self) -> None:
        class User(RootEntity):
            id: IntId

        with pytest.raises(ModelValidationError):
            build(User)


# ── events_of ────────────────────────────────────────────────────────────────


class TestEventsOf:
    def test_returns_events_from_emitter(self) -> None:
        class UserCreated(Event):
            user_id: int

        class User(RootEntity):
            id: IntId

            def __post_init__(self) -> None:
                self._event_emitter.emit(UserCreated(user_id=self.id.value))

        u = User(id=IntId(value=1))
        evts = events_of(u)
        assert len(evts) == 1
        assert isinstance(evts[0], UserCreated)
        assert evts[0].user_id == 1

    def test_empty_when_no_events(self) -> None:
        class User(RootEntity):
            id: IntId

        u = build(User, id=IntId(value=1))
        assert events_of(u) == []


# ── assert_event_emitted ─────────────────────────────────────────────────────


class TestAssertEventEmitted:
    def test_returns_matching_event(self) -> None:
        class OrderPlaced(Event):
            order_id: int

        events = [OrderPlaced(order_id=1)]
        e = assert_event_emitted(events, OrderPlaced, order_id=1)
        assert e.order_id == 1

    def test_raises_on_no_match(self) -> None:
        class OrderPlaced(Event):
            order_id: int

        with pytest.raises(AssertionError):
            assert_event_emitted([], OrderPlaced, order_id=1)

    def test_checks_all_attributes(self) -> None:
        class UserCreated(Event):
            user_id: int
            name: str

        events = [UserCreated(user_id=5, name="Alf")]
        e = assert_event_emitted(events, UserCreated, user_id=5, name="Alf")
        assert e.name == "Alf"

    def test_raises_on_wrong_attribute(self) -> None:
        class UserCreated(Event):
            user_id: int

        events = [UserCreated(user_id=5)]
        with pytest.raises(AssertionError):
            assert_event_emitted(events, UserCreated, user_id=99)


# ── assert_no_events ─────────────────────────────────────────────────────────


class TestAssertNoEvents:
    def test_passes_on_empty(self) -> None:
        assert_no_events([])

    def test_raises_on_non_empty(self) -> None:
        class OrderPlaced(Event):
            order_id: int

        with pytest.raises(AssertionError):
            assert_no_events([OrderPlaced(order_id=1)])


# ── check_invariant ──────────────────────────────────────────────────────────


class TestCheckInvariant:
    def test_field_invariance_passes(self) -> None:
        class User(RootEntity):
            id: IntId
            username: str | None = None

            @field_invariance("username")
            def username_must_not_be_empty(cls, value: str) -> str:
                if not value.strip():
                    raise ValueError("username must not be empty")
                return value

        check_invariant(User, "username_must_not_be_empty", id=IntId(value=1), username="Alf")

    def test_field_invariance_raises(self) -> None:
        class User(RootEntity):
            id: IntId
            username: str | None = None

            @field_invariance("username")
            def username_must_not_be_empty(cls, value: str) -> str:
                if not value.strip():
                    raise ValueError("username must not be empty")
                return value

        with pytest.raises(InvarianceException):
            check_invariant(User, "username_must_not_be_empty", id=IntId(value=1), username="")

    def test_model_invariance_passes(self) -> None:
        class User(RootEntity):
            id: IntId
            username: str | None = None
            age: int

            @invariance
            def adult(self) -> None:
                if self.age < 18:
                    raise ValueError("must be adult")

        check_invariant(User, "adult", id=IntId(value=1), username="Alf", age=20)

    def test_model_invariance_raises(self) -> None:
        class User(RootEntity):
            id: IntId
            username: str | None = None
            age: int

            @invariance
            def adult(self) -> None:
                if self.age < 18:
                    raise ValueError("must be adult")

        with pytest.raises(InvarianceException):
            check_invariant(User, "adult", id=IntId(value=1), username="Alf", age=15)

    def test_raises_on_unknown_name(self) -> None:
        class User(RootEntity):
            id: IntId
            username: str | None = None

        with pytest.raises(ValueError, match="does_not_exist"):
            check_invariant(User, "does_not_exist", id=IntId(value=1), username="Alf")
