from datetime import datetime, timedelta, timezone

from aod._internal.core.event_emitter import Event
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.value_object import ValueObject


def test_value_object_emit_poll_clear() -> None:
    class Price(ValueObject):
        amount: int

    p = Price(amount=10)
    e1 = Event()
    p._emit(e1)

    assert p.poll_events() == [e1]
    p._clear_events()
    assert p.poll_events() == []


def test_entity_poll_includes_child_emitters_sorted_by_time() -> None:
    class MutableEvent:
        def __init__(self, emmited_at: datetime):
            self.emmited_at = emmited_at

    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=1)
    t2 = t0 + timedelta(seconds=2)

    class Child(RootEntity):
        id: int

    class Parent(RootEntity):
        child: Child

    child = Child(id=1)
    parent = Parent(child=child)

    e_parent = MutableEvent(emmited_at=t1)
    e_child_early = MutableEvent(emmited_at=t0)
    e_child_late = MutableEvent(emmited_at=t2)

    parent._emit(e_parent)  # type: ignore
    child._emit(e_child_early)  # type: ignore
    child._emit(e_child_late)  # type: ignore

    assert parent.poll_events() == [e_child_early, e_parent, e_child_late]


def test_entity_clear_clears_children_events_too() -> None:
    class Child(Entity, root=True):
        id: int

    class Parent(RootEntity):
        child: Child

    child = Child(id=1)
    parent = Parent(child=child)

    parent._emit(Event())
    child._emit(Event())

    assert len(parent.poll_events()) == 2
    parent._clear_events()
    assert parent.poll_events() == []
