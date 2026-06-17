# Event System

Domain Events record something that happened in your domain. They are immutable, auto-timestamped, and automatically collected by use cases.

## Event

`Event` is an immutable base class for all domain events. Events cannot be changed after construction.

### Class Definition

```python
from aod.events import Event


class OrderPlaced(Event):
    order_id: str
    total: float
```

### Constructor Parameters

`Event.__init__()` accepts keyword arguments for every annotated field on the subclass. The `emitted_at` field is set automatically and cannot be passed by the user.

| Parameter | Type | Description |
|-----------|------|-------------|
| `order_id` | `str` | Identifier of the placed order. Required |
| `total` | `float` | Order total amount. Required |
| `emitted_at` | — | Auto-set by the framework. Not user-settable (`init=False`) |

```python
from aod.events import Event


class OrderPlaced(Event):
    order_id: str
    total: float

event = OrderPlaced(order_id="1", total=99.99)
assert event.order_id == "1"
assert event.total == 99.99
assert event.emitted_at is not None
```

## Key Characteristics

### Immutable

Events cannot be changed after creation. Any attribute assignment raises `MutationForbiddenException`:

```python
event.order_id = "2"  # MutationForbiddenException!
```

### Auto-Timestamped

Every event has an `emitted_at` field that is automatically set to `datetime.now(timezone.utc)` at construction time:

```python
from datetime import datetime

event = OrderPlaced(order_id="1", total=99.99)
assert isinstance(event.emitted_at, datetime)
```

The `emitted_at` field is defined as:

| Field | Type | Default | Description |
|-----------|------|---------|-------------|
| `emitted_at` | `datetime` | `Field(default_factory=lambda: datetime.now(timezone.utc), init=False)` | UTC timestamp of when the event was created. Cannot be set by the user |

### Structural Equality

Two events with the same attribute values are equal:

```python
e1 = OrderPlaced(order_id="1", total=99.99)
e2 = OrderPlaced(order_id="1", total=99.99)
assert e1 == e2  # True — same attributes
```

## Emitting Events

### `EventEmitter`

Every domain object (Entity, RootEntity, ValueObject, Service) has a `_event_emitter` instance for emitting events.

```python
class EventEmitter:
    def emit(self, event: Event) -> None: ...
    def poll_events(self) -> list[Event]: ...
    def clear_events(self) -> None: ...
```

#### `emit()`

| Parameter | Type | Description |
|-----------|------|-------------|
| `event` | `Event` | The event instance to record |

Appends the event to the emitter's internal list. If an `EventCollector` context is active, also appends to the collector's list.

#### `poll_events()`

| Parameter | Type | Description |
|-----------|------|-------------|
| (none) | — | — |

Returns `list[Event]` — a copy of all events emitted by this emitter, leaving the internal list intact.

#### `clear_events()`

| Parameter | Type | Description |
|-----------|------|-------------|
| (none) | — | — |

Clears all events from the internal list.

### From Entities

```python
from aod.domain import RootEntity


class OrderPlaced(Event):
    order_id: str
    total: float


class Order(RootEntity):
    id: str
    total: float

    def place(self) -> None:
        self._event_emitter.emit(OrderPlaced(order_id=self.id, total=self.total))
```

### From Value Objects

```python
class MoneyChanged(Event):
    old_amount: float
    new_amount: float


class Money(ValueObject):
    amount: float
    currency: str

    def update_amount(self, new_amount: float) -> Money:
        old = self.amount
        return Money(amount=new_amount, currency=self.currency)
```

### From Services

```python
class OrderService(Service):
    def process_order(self, order: Order) -> None:
        self._event_emitter.emit(OrderProcessed(order_id=order.id))
```

## Collecting Events

### Automatic Collection by UseCases

Use cases automatically collect events from all domain objects touched during `run()`. The collected events are available via `self.events` after execution.

```python
from aod.application import UseCase, CommandPort


class PlaceOrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]

    def run(self, order_id: str, total: float) -> None:
        order = Order(id=order_id, total=total)
        order.place()
        self.place_order.handle(PlaceOrder(
            order_id=order_id, total=total,
        ))

uc = PlaceOrderUseCase(place_order=handler)
uc.run(order_id="1", total=99.99)
assert len(uc.events) == 1
assert isinstance(uc.events[0], OrderPlaced)
```

### Manual Collection with `EventCollector`

`EventCollector` is a context manager that captures all events emitted by any domain object within its scope, in addition to each emitter's own storage.

```python
from aod.events import EventCollector


with EventCollector() as events:
    order.place()
    order.ship()
    user.notify()

assert len(events) == 3
```

#### `EventCollector.__init__()`

| Parameter | Type | Description |
|-----------|------|-------------|
| (none) | — | No parameters |

#### `EventCollector.__enter__()`

| Parameter | Type | Description |
|-----------|------|-------------|
| (none) | — | — |

Returns `list[Event]` — the same list that events will be appended to while the context is active.

#### `EventCollector.__exit__()`

| Parameter | Type | Description |
|-----------|------|-------------|
| `*args` | `object` | Standard context manager exit arguments |

Stops event collection so subsequent events are no longer captured.

## Event Assertions

### `events_of()`

```python
from aod.testing import events_of

order = Order(id="1", total=99.99)
order.place()
order.ship()

events = events_of(order)
assert len(events) == 2
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `obj` | `Entity \| ValueObject \| Service` | The domain object to extract events from |

Returns `list[Event]`.

### `assert_event_emitted()`

```python
from aod.testing import assert_event_emitted

assert_event_emitted(events, OrderPlaced, order_id="1")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `events` | `Sequence[Event]` | Sequence of events to search through |
| `event_type` | `type[Event]` | The expected event class |
| `**attrs` | `Any` | Key-value pairs of expected attribute values on the event |

Returns the matching `Event` instance. Raises `AssertionError` if no match.

### `assert_no_events()`

```python
from aod.testing import assert_no_events

assert_no_events(events)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `events` | `Sequence[Event]` | Sequence of events to check |

Raises `AssertionError` if the sequence is non-empty.

## Complex Events

Events can contain complex data types including optional fields and nested types:

```python
from typing import Optional
from datetime import datetime


class OrderShipped(Event):
    order_id: str
    shipped_at: datetime
    tracking_number: Optional[str] = None

event = OrderShipped(
    order_id="1",
    shipped_at=datetime.now(),
    tracking_number="TRACK-123",
)
```

### Parameters for Complex Events

| Parameter | Type | Description |
|-----------|------|-------------|
| `order_id` | `str` | Order identifier. Required |
| `shipped_at` | `datetime` | Timestamp of shipment. Required |
| `tracking_number` | `Optional[str]` | Shipping tracking number. Optional, defaults to `None` |

## Event Inheritance

Events can form a hierarchy:

```python
class BaseOrderEvent(Event):
    order_id: str

class OrderPlaced(BaseOrderEvent):
    total: float

class OrderShipped(BaseOrderEvent):
    tracking_number: str
```

When inheriting, each subclass adds its own fields as constructor parameters on top of the parent's fields:

`OrderPlaced.__init__()` parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `order_id` | `str` | Inherited from `BaseOrderEvent`. Required |
| `total` | `float` | Order total. Required |

`OrderShipped.__init__()` parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `order_id` | `str` | Inherited from `BaseOrderEvent`. Required |
| `tracking_number` | `str` | Shipping tracking number. Required |

## Testing

```python
from aod.testing import build, events_of, assert_event_emitted, assert_no_events

order = build(Order, id="1", total=99.99)
order.place()

events = events_of(order)
assert len(events) == 1

assert_event_emitted(events, OrderPlaced, order_id="1")

order2 = build(Order, id="2", total=0.0)
assert_no_events(event_of(order2))
```

## Exceptions

| Exception | Raised When |
|-----------|-------------|
| `MutationForbiddenException` | Attempting to mutate an event field after creation |

## Next Steps

- [Entity & RootEntity](entities.md) — Learn about emitting events from entities
- [ValueObject](value-objects.md) — Learn about emitting events from value objects
- [Service](services.md) — Learn about emitting events from services
- [Use Cases](../application/use-cases.md) — Learn about automatic event collection