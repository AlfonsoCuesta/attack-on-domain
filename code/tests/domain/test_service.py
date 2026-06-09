from __future__ import annotations

import pytest
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.core.event_emitter import Event, EventCollector, EventEmitter
from aod._internal.domain.service import Service


class OrderShipped(Event):
    order_id: int


class ShippingService(Service):
    def ship(self, order_id: int) -> None:
        self._event_emitter.emit(OrderShipped(order_id=order_id))


class NotificationService(Service):
    sent: list[str] = []

    def notify(self, message: str) -> None:
        self.sent.append(message)


def test_service_can_be_instantiated() -> None:
    srv = ShippingService()
    assert isinstance(srv, Service)


def test_service_has_event_emitter() -> None:
    srv = ShippingService()
    assert hasattr(srv, "_event_emitter")
    assert isinstance(srv._event_emitter, EventEmitter)


def test_service_can_emit_events() -> None:
    srv = ShippingService()
    srv.ship(order_id=42)
    events = srv._event_emitter.poll_events()
    assert len(events) == 1
    assert isinstance(events[0], OrderShipped)
    assert events[0].order_id == 42


def test_service_events_collected_by_event_collector() -> None:
    srv = ShippingService()
    with EventCollector() as collected:
        srv.ship(order_id=7)
    assert len(collected) == 1
    assert collected[0].order_id == 7


def test_service_multiple_events() -> None:
    srv = ShippingService()
    srv.ship(order_id=1)
    srv.ship(order_id=2)
    events = srv._event_emitter.poll_events()
    assert len(events) == 2
    assert events[0].order_id == 1
    assert events[1].order_id == 2


def test_service_events_not_shared_across_instances() -> None:
    srv1 = ShippingService()
    srv2 = ShippingService()
    srv1.ship(order_id=1)
    assert len(srv2._event_emitter.poll_events()) == 0


def test_service_is_immutable_cannot_set_fields() -> None:
    srv = ShippingService()
    with pytest.raises(MutationForbiddenException):
        srv.ship = lambda x: None  # type: ignore


def test_service_is_immutable_cannot_set_private_field() -> None:
    srv = ShippingService()
    with pytest.raises(MutationForbiddenException):
        srv._event_emitter = EventEmitter()


def test_service_is_immutable_cannot_del_fields() -> None:
    srv = ShippingService()
    with pytest.raises(MutationForbiddenException):
        del srv._event_emitter


def test_service_public_method_allows_self_mutation() -> None:
    srv = NotificationService()
    srv.notify("hello")
    assert srv.sent == ["hello"]


def test_service_repr() -> None:
    srv = ShippingService()
    rep = repr(srv)
    assert "ShippingService" in rep


def test_service_post_init_runs() -> None:
    called: list[bool] = []

    class InitService(Service):
        def __post_init__(self) -> None:
            called.append(True)

        def work(self) -> None:
            pass

    InitService()
    assert called == [True]


def test_service_post_init_can_emit_events() -> None:
    class InitEmitter(Service):
        label: str = "default"

        def __post_init__(self) -> None:
            self._event_emitter.emit(OrderShipped(order_id=0))

    srv = InitEmitter()
    events = srv._event_emitter.poll_events()
    assert len(events) == 1


def test_service_inheritance() -> None:
    class BaseService(Service):
        def base_method(self) -> str:
            return "base"

    class ChildService(BaseService):
        def child_method(self) -> str:
            return "child"

    child = ChildService()
    assert child.base_method() == "base"
    assert child.child_method() == "child"


def test_service_inheritance_preserves_event_emitter() -> None:
    class BaseService(Service):
        def base_emit(self) -> None:
            self._event_emitter.emit(OrderShipped(order_id=1))

    class ChildService(BaseService):
        def child_emit(self) -> None:
            self._event_emitter.emit(OrderShipped(order_id=2))

    child = ChildService()
    child.base_emit()
    child.child_emit()
    events = child._event_emitter.poll_events()
    assert len(events) == 2


def test_service_allows_private_methods() -> None:
    class PrivateMethodService(Service):
        def _helper(self) -> int:
            return 42

        def get_value(self) -> int:
            return self._helper()

    srv = PrivateMethodService()
    assert srv.get_value() == 42


def test_service_can_be_mutated_via_public_method() -> None:
    class MutateService(Service):
        counter: int = 0

        def increment(self) -> None:
            self.counter += 1

    srv = MutateService()
    srv.increment()
    assert srv.counter == 1


def test_service_with_no_public_methods() -> None:
    srv = Service()
    assert isinstance(srv, Service)


def test_service_event_emitter_isolation() -> None:
    srv1 = ShippingService()
    srv2 = ShippingService()
    srv1.ship(order_id=10)
    srv2.ship(order_id=20)
    e1 = srv1._event_emitter.poll_events()
    e2 = srv2._event_emitter.poll_events()
    assert len(e1) == 1
    assert e1[0].order_id == 10
    assert len(e2) == 1
    assert e2[0].order_id == 20


def test_service_many_emits() -> None:
    srv = ShippingService()
    for i in range(100):
        srv.ship(order_id=i)
    events = srv._event_emitter.poll_events()
    assert len(events) == 100
    assert events[-1].order_id == 99


def test_service_events_cleared() -> None:
    srv = ShippingService()
    srv.ship(order_id=1)
    srv._event_emitter.clear_events()
    assert srv._event_emitter.poll_events() == []
