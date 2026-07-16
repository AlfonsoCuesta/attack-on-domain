from aod._internal.core.event_emitter import Event, EventCollector, EventEmitter, IntegrationEvent
from aod._internal.core.fields.fields import Field
from aod._internal.domain.entity import RootEntity
from aod._internal.domain.value_object import ValueObject


def test_integration_event_is_subclass_of_event() -> None:
    assert issubclass(IntegrationEvent, Event)


def test_integration_event_is_instance_of_event() -> None:
    event = IntegrationEvent()
    assert isinstance(event, Event)
    assert isinstance(event, IntegrationEvent)


def test_event_collector_domain_events_excludes_integration_events() -> None:
    domain = Event()
    integration = IntegrationEvent()

    with EventCollector() as events:
        events.append(domain)
        events.append(integration)

    assert domain in events.domain_events
    assert integration not in events.domain_events


def test_event_collector_integration_events_only_integration() -> None:
    domain = Event()
    integration = IntegrationEvent()

    with EventCollector() as events:
        events.append(domain)
        events.append(integration)

    assert integration in events.integration_events
    assert domain not in events.integration_events


def test_event_collector_separation_via_emit_with_collector() -> None:
    class MyDomainEvent(Event):
        pass

    class MyIntegrationEvent(IntegrationEvent):
        pass

    domain_event = MyDomainEvent()
    integration_event = MyIntegrationEvent()

    emitter = EventEmitter()
    with EventCollector() as events:
        emitter.emit(domain_event)
        emitter.emit(integration_event)

    assert len(events) == 2
    assert len(events.domain_events) == 1
    assert len(events.integration_events) == 1
    assert events.domain_events[0] is domain_event
    assert events.integration_events[0] is integration_event


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
        id: int = Field(id=True)

    child = Child(id=1)
    e1 = Event()
    child._event_emitter.emit(e1)

    assert child._event_emitter.poll_events() == [e1]
    child._event_emitter.clear_events()
    assert child._event_emitter.poll_events() == []


def test_event_collector_captures_from_entity() -> None:
    class Child(RootEntity):
        id: int = Field(id=True)

    child = Child(id=1)

    with EventCollector() as events:
        child._event_emitter.emit(Event())

    assert len(events) == 1


def test_event_collector_captures_from_aggregate() -> None:
    class Child(RootEntity):
        id: int = Field(id=True)

    class Parent(RootEntity):
        id: int = Field(id=True)
        child: Child

    child = Child(id=1)
    parent = Parent(id=1, child=child)

    with EventCollector() as events:
        parent._event_emitter.emit(Event())
        child._event_emitter.emit(Event())

    assert len(events) == 2
