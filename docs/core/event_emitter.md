# Event System

## Purpose

Domain Event pattern with context-based event collection across aggregate boundaries.

## Event(BaseSealed)

An immutable event with an auto-set timestamp:

```python
class Event(BaseSealed):
    emitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), init=False
    )
```

Note: `emitted_at` is auto-set at construction.

## EventEmitter

Concrete class (not a Protocol). Manages a list of events per object:

```python
class EventEmitter:
    def emit(self, event: Event) -> None:
        # 1. appends to self._events (local storage)
        # 2. if EventCollector is active via ContextVar, appends there too

    def poll_events(self) -> list[Event]:
        return list(self._events)  # returns a copy

    def clear_events(self) -> None:
        self._events.clear()
```

Every domain object (`Entity`, `ValueObject`, `Service`) declares `_event_emitter` as a `PrivateField` with a `default_factory`, so Pydantic creates the emitter automatically:

```python
from aod import PrivateField
from aod._internal.core.event_emitter import EventEmitter

_event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)
```

`EventEmitter` itself is not exported from `aod` — it's an internal
implementation detail accessed via the `_event_emitter: EventEmitter`
`PrivateField` on domain objects. Users import `EventCollector` from
`aod` for inter-aggregate event capture.

## EventCollector

A context manager that captures all events emitted within its scope,
across aggregate boundaries. Designed for testing or for flushing
domain events to an outbox at the end of a use case.

```python
from aod import EventCollector

with EventCollector() as events:
    order.place(item)
    order.ship()
# events contains OrderPlaced and OrderShipped
```

### API quirk: `__enter__` returns the list, not the collector

`EventCollector.__enter__` returns the underlying `list[Event]`, not
the collector instance:

```python
with EventCollector() as events:
    type(events)  # list[Event]
```

This is intentional: the common case is to inspect the captured
events (`events[-1]`, `len(events)`, etc.) directly. The collector
itself doesn't expose methods that need a reference.

### How it works

1. On `__enter__`, sets a `ContextVar` pointing to its own event list
2. `EventEmitter.emit()` always appends to the emitter's local
   storage, AND — if the ContextVar is set — appends there too
3. On `__exit__`, resets the ContextVar

This means a single `emit()` call can land in two places (the
emitter's history and any active collector). The two are independent
lists.

### ContextVar isolation

The collector state lives in a `ContextVar`, which is per-task (and
per-thread, in legacy threads). Concurrent collectors in the same
task are not supported — the inner collector wins, and on exit the
outer one is restored but its list is unaffected.

```python
_event_collector: ContextVar[list[Event]] = ContextVar("_event_collector")
```

### Limitations

- The contents of the captured list are the original `Event`
  instances, not proxies — they can be inspected freely but not
  mutated (`Event` is `BaseSealed` anyway).

## Usage Pattern

```python
# Emit an event
self._event_emitter.emit(MyEvent(data=...))

# Collect events from an aggregate operation
with EventCollector() as collected:
    root.do_business_logic()
    # collected is populated automatically
```
