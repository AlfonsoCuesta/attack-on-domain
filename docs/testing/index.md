# Testing Utilities

The framework provides testing utilities for building domain objects, inspecting events, and using spy doubles for ports and infrastructure.

## Imports

```python
from aod.testing import build, events_of, assert_event_emitted, assert_no_events, check_invariant
from aod.testing import FakeDomain
from aod.testing.doubles import SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache, SpySession, SpyAsyncSession
```

Async spies use plain names from a separate module:

```python
from aod.testing.doubles.application.async_ import SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache
```

## Helper Functions

### `build`

```python
def build(cls: type[T], **kwargs: Any) -> T
```

Create an instance of a domain class skipping validation.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `cls` | `type[T]` | The class to instantiate. Must be an `Entity`, `RootEntity`, `ValueObject`, or any `BaseValidator` subclass. |
| `**kwargs` | `Any` | Field values to set on the instance. |

#### Returns

`T` — An instance of `cls` without validation.

```python
user = build(User, id=1, name="Alice")
```

### `events_of`

```python
def events_of(obj: BaseGuarded) -> list[Event]
```

Extract all events emitted by a domain object via its `_event_emitter`.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `obj` | `BaseGuarded` | The domain object (`Entity`, `ValueObject`, `Service`, etc.). |

#### Returns

`list[Event]` — All events emitted by the object since construction or last clear.

```python
events = events_of(user)
```

### `assert_event_emitted`

```python
def assert_event_emitted(events: Sequence[Event], event_type: type[Event], **attrs: Any) -> Event
```

Assert that a specific event type was emitted with matching field values.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `events` | `Sequence[Event]` | The list of events to search (from `events_of()`). |
| `event_type` | `type[Event]` | The expected event class. |
| `**attrs` | `Any` | Field values that the event must match. |

#### Returns

`Event` — The matching event instance.

#### Raises

`AssertionError` — If no matching event is found.

```python
events = events_of(user)
assert_event_emitted(events, UserCreatedEvent, user_id=1)
```

### `assert_no_events`

```python
def assert_no_events(events: Sequence[Event]) -> None
```

Assert that no events were emitted.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `events` | `Sequence[Event]` | The list of events to check. |

#### Raises

`AssertionError` — If any events exist.

```python
assert_no_events(events_of(service))
```

### `check_invariant`

```python
def check_invariant(
    cls: type,
    invariant_name: str,
    data: dict[str, Any] | None = None,
    **kwargs: Any,
) -> None
```

Run a single invariant validator against an instance created via `build()`.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `cls` | `type` | The class that defines the invariant. |
| `invariant_name` | `str` | The name of the invariant validator function. |
| `data` | `dict[str, Any] \| None` | Optional dictionary of field values. |
| `**kwargs` | `Any` | Additional field values (merged with `data`). |

#### Raises

- `ValueError` — If no invariant with that name exists on the class.
- `InvarianceException` — If the invariant validation fails.

```python
check_invariant(User, "valid_email", email="not-an-email")
```

## Spy Classes

### SpyLogger

```python
from aod.testing.doubles import SpyLogger
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `debug` | `debug(self, msg: str, **context: object)` | Log a debug message. |
| `info` | `info(self, msg: str, **context: object)` | Log an info message. |
| `warning` | `warning(self, msg: str, **context: object)` | Log a warning message. |
| `error` | `error(self, msg: str, **context: object)` | Log an error message. |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `msg` | `str` | The log message. |
| `**context` | `object` | Additional context key-value pairs. |

#### Property

- `entries: list[LogEntry]` — All logged entries. Each `LogEntry` has:
  - `.level: str` — The log level ("debug", "info", "warning", "error").
  - `.msg: str` — The log message.
  - `.context: dict[str, object]` — The context key-value pairs.

### SpyEventBus

```python
from aod.testing.doubles import SpyEventBus
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `publish` | `publish(self, *events: Event)` | Record published events. |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `*events` | `Event` | One or more events to publish. |

#### Property

- `published: list[Event]` — All events that have been published.

### SpyUnitOfWork

```python
from aod.testing.doubles import SpyUnitOfWork
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `begin` | `begin(self)` | No-op. |
| `commit` | `commit(self)` | Set `committed = True`. |
| `rollback` | `rollback(self)` | Set `rolled_back = True`. |

#### Properties

- `committed: bool` — Whether `commit()` was called.
- `rolled_back: bool` — Whether `rollback()` was called.

### SpyCache

```python
from aod.testing.doubles import SpyCache
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `get` | `get(self, key: str) -> Any` | Retrieve a value by key from the in-memory store. |
| `set` | `set(self, key: str, value: Any, ttl: float \| None = None)` | Store a value by key. |
| `delete` | `delete(self, key: str)` | Remove a value by key. |
| `flush` | `flush(self)` | Clear the in-memory store. |
| `set_promise` | `set_promise(self, key: str, value: Any, ttl: float \| None = None)` | Record a set-promise call. |
| `delete_promise` | `delete_promise(self, key: str)` | Record a delete-promise call. |

#### Properties

- `get_calls: list[str]` — Keys passed to `get()`.
- `set_calls: list[tuple[str, Any, float | None]]` — Arguments passed to `set()`.
- `delete_calls: list[str]` — Keys passed to `delete()`.
- `flush_calls: list[None]` — Records each `flush()` call.

### SpySession

```python
from aod.testing.doubles import SpySession
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `execute` | `execute(self, operation: object) -> object` | Record the operation and return `_execute_result`. |
| `query` | `query(self, operation: object) -> object` | Record the operation and return `_query_result`. |
| `begin` | `begin(self)` | Record a begin call. |
| `commit` | `commit(self)` | Record a commit call. |
| `rollback` | `rollback(self)` | Record a rollback call. |
| `close` | `close(self)` | Record a close call. |
| `is_dirty` | `is_dirty(self) -> bool` | Return the `_dirty` flag. |
| `set_dirty` | `set_dirty(self, dirty: bool)` | Set the dirty flag. |

#### Properties

- `execute_calls: list[object]` — Operations passed to `execute()`.
- `query_calls: list[object]` — Operations passed to `query()`.
- `begin_calls`, `commit_calls`, `rollback_calls`, `close_calls: list[None]` — Lifecycle call tracking.

### SpyAsyncSession

```python
from aod.testing.doubles import SpyAsyncSession
```

Same methods as `SpySession` but `execute`, `query`, `begin`, `commit`, `rollback`, and `close` are async. `is_dirty()` and `set_dirty()` remain sync.

## Async Spies

Import async spy variants from the dedicated module using plain names:

```python
from aod.testing.doubles.application.async_ import SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache
```

Each variant mirrors the sync API but with async methods:

| Class | Async Methods |
|-------|---------------|
| `SpyLogger` | `debug`, `info`, `warning`, `error` |
| `SpyEventBus` | `publish` |
| `SpyUnitOfWork` | `begin`, `commit`, `rollback` |
| `SpyCache` | `get`, `set`, `delete`, `flush` |

`set_promise()` and `delete_promise()` remain sync on `AsyncSpyCache`.

## FakeDomain

```python
from aod.testing import FakeDomain
```

`FakeDomain(Generic[T])` generates test data for domain objects.

### Constructor

`FakeDomain(model_cls: type[T], **defaults: Any)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_cls` | `type[T]` | The domain class to build. Must be `Entity`, `RootEntity`, or `ValueObject`. |
| `**defaults` | `Any` | Default values for specific fields. |

### `__call__`

```python
def __call__(self, **overrides: Any) -> T
```

Build an instance with auto-generated fields for any not provided.

| Parameter | Type | Description |
|-----------|------|-------------|
| `**overrides` | `Any` | Field values to override. |

#### Returns

`T` — An instance of the domain class built via `reconstruct()`.

### `batch`

```python
def batch(self, count: int, overrides_list: list[dict[str, Any]] | None = None) -> list[T]
```

Build multiple instances.

| Parameter | Type | Description |
|-----------|------|-------------|
| `count` | `int` | Number of instances to build. |
| `overrides_list` | `list[dict[str, Any]] \| None` | Optional list of per-instance overrides. |

```python
users = FakeDomain(User)
alice = users(name="Alice")  # auto-generates other fields
batch = users.batch(5)       # 5 users with auto-generated fields
```

## Common Testing Patterns

### Testing Use Cases

```python
from aod.testing.doubles import SpyUnitOfWork, SpyEventBus, SpyLogger
from aod.infrastructure import inject_adapters

class MyContainer(AdapterContainerBase):
    pass

container = MyContainer()
use_case = inject_adapters(
    container,
    CreateUser,
    uow=SpyUnitOfWork(),
    event_bus=SpyEventBus(),
    logger=SpyLogger(),
)
use_case.run(user_id=1, name="Alice")

assert use_case.uow.committed
assert_event_emitted(use_case.events, UserCreatedEvent, user_id=1)
```

### Testing Entities

```python
from aod.testing import build, events_of, assert_event_emitted

class User(RootEntity):
    id: int
    name: str

    def __post_init__(self) -> None:
        self._event_emitter.emit(UserCreatedEvent(user_id=self.id))

user = build(User, id=1, name="Alice")
events = events_of(user)
assert_event_emitted(events, UserCreatedEvent, user_id=1)
```

### Testing Value Objects

```python
from aod.testing import build

class Address(ValueObject):
    street: str
    city: str

addr = build(Address, street="123 Main", city="NYC")
```

## Next Steps

- [API Reference: Full class and method list](../api/index.md)