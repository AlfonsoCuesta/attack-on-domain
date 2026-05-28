# Event System

## Purpose

Domain Event pattern with context-based event collection across aggregate boundaries.

## Event(BaseImmutable)

An immutable event with an auto-set timestamp:

```python
class Event(BaseImmutable):
    emmited_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), init=False
    )
```

Note: `emmited_at` is a known typo (should be `emitted_at`). Do NOT fix — it's established API.

## EventEmitter

Concrete class (not a Protocol). Manages a list of events per object:

```python
class EventEmitter:
    def emit(self, event: Event) -> None:
        # 1. appends to self._events (local storage)
        # 2. if EventCollector is active via ContextVar, appends there too

    def poll_events(self) -> List[Event]:
        return list(self._events)  # returns a copy

    def clear_events(self) -> None:
        self._events.clear()
```

Every domain object (`ValueObject`, `Entity`, `Service`) creates an `EventEmitter` in `__init__`:

```python
object.__setattr__(self, "_event_emitter", EventEmitter())
```

## EventCollector

A context manager that captures all events emitted within its scope:

```python
with EventCollector() as events:
    entity.do_something()
    child.do_something()
# events now has all emitted events from both entities
```

### How it works
1. On `__enter__`, it sets a `ContextVar` pointing to its own event list
2. `EventEmitter.emit()` checks if the ContextVar is active; if so, appends there too
3. On `__exit__`, it resets the ContextVar

### ContextVar

```python
_event_collector: ContextVar[List[Event]] = ContextVar("_event_collector")
```

Accessed via `_event_collector.get(None)` — returns `None` if no collector is active.

## Usage Pattern

```python
# Emit an event
self._event_emitter.emit(MyEvent(data=...))

# Collect events from an aggregate operation
with EventCollector() as collected:
    root.do_business_logic()
    # collected is populated automatically
```
