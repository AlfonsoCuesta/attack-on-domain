from aod._internal.core.event_emitter import Event, EventCollector, EventEmitter
from aod._internal.domain.entity import EntityId, RootEntity
from aod._internal.domain.value_object import ValueObject


class IntId(EntityId):
    value: int


def test_value_object_emit_poll_clear() -> None:
    class Price(ValueObject):
        amount: int

    p = Price(amount=10)
    e1 = Event()
    p._event_emitter.emit(e1)

    assert p._event_emitter.poll_events() == [e1]
    p._event_emitter.clear_events()
    assert p._event_emitter.poll_events() == []


def test_event_emitter_emit_poll_clear() -> None:
    emitter = EventEmitter()
    e1 = Event()
    emitter.emit(e1)

    assert emitter.poll_events() == [e1]
    emitter.clear_events()
    assert emitter.poll_events() == []


def test_event_collector_captures_emitted_events() -> None:
    class Price(ValueObject):
        amount: int

    p = Price(amount=10)

    with EventCollector() as events:
        p._event_emitter.emit(Event())
        p._event_emitter.emit(Event())

    assert len(events) == 2


def test_event_collector_does_not_capture_outside_context() -> None:
    class Price(ValueObject):
        amount: int

    p = Price(amount=10)

    e1 = Event()
    p._event_emitter.emit(e1)

    assert p._event_emitter.poll_events() == [e1]


def test_entity_emit_poll_clear() -> None:
    class Child(RootEntity):
        id: IntId

    child = Child(id=IntId(value=1))
    e1 = Event()
    child._event_emitter.emit(e1)

    assert child._event_emitter.poll_events() == [e1]
    child._event_emitter.clear_events()
    assert child._event_emitter.poll_events() == []


def test_event_collector_captures_from_entity() -> None:
    class Child(RootEntity):
        id: IntId

    child = Child(id=IntId(value=1))

    with EventCollector() as events:
        child._event_emitter.emit(Event())

    assert len(events) == 1


def test_event_collector_captures_from_aggregate() -> None:
    class Child(RootEntity):
        id: IntId

    class Parent(RootEntity):
        id: IntId
        child: Child

    child = Child(id=IntId(value=1))
    parent = Parent(id=IntId(value=1), child=child)

    with EventCollector() as events:
        parent._event_emitter.emit(Event())
        child._event_emitter.emit(Event())

    assert len(events) == 2
