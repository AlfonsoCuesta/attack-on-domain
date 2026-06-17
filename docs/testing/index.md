# Testing Utilities

The framework provides testing utilities for building domain objects, inspecting events, and creating stub containers for integration testing.

## Imports

```python
from aod.testing import build, events_of, assert_event_emitted, assert_no_events, check_invariant
from aod.testing import FakeDomain
from aod.testing.doubles import (
    SpySession,
    SpyAsyncSession,
    SpyLogger,
    SpyEventBus,
    SpyCache,
    port_stub,
    spy_adapter_container,
)
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
| `cls` | `type[T]` | The class to instantiate. Must be an `Entity`, `RootEntity`, `ValueObject`, or any domain object subclass. |
| `**kwargs` | `Any` | Field values to set on the instance. |

#### Returns

`T` — An instance of `cls` without validation.

```python
user = build(User, id=1, name="Alice")
```

### `events_of`

```python
def events_of(obj: object) -> list[Event]
```

Extract all events emitted by a domain object via its `_event_emitter`.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `obj` | `object` | The domain object (`Entity`, `ValueObject`, `Service`, etc.). |

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

```python
events = events_of(user)
assert_event_emitted(events, UserCreatedEvent, user_id=1)
```

### `assert_no_events`

```python
def assert_no_events(events: Sequence[Event]) -> None
```

Assert that no events were emitted.

```python
assert_no_events(events_of(service))
```

### `check_invariant`

```python
def check_invariant(cls: type, invariant_name: str, data: dict[str, Any] | None = None, **kwargs: Any) -> None
```

Run a single invariant validator against an instance created via `build()`.

```python
check_invariant(User, "valid_email", email="not-an-email")
```

## Container Testing with `spy_adapter_container`

The recommended approach for testing use cases is to create a spy version of your container. This replaces sessions and ports with stubs that record calls and let you configure return values.

```python
from aod.testing.doubles import spy_adapter_container

class AppContainer(AdapterContainerBase):
    sessions: set = {MySession}
    handlers: list = [CreateUserHandler, GetUserHandler]

# Create a spy container (all sessions become stubs)
container = spy_adapter_container(AppContainer())

# Configure session behavior
container.get_session_stub(MySession).is_dirty.returns(True)
container.get_session_stub(MySession).begin.always_returns(None)

# Configure port behavior (optional)
container.get_port_stub(Logger).info.always_returns(None)

# Inject and run
use_case = inject_adapters(container, CreateUserUseCase)
use_case.run(user_id=1, name="Alice")

# Assert handler was called
handler = container.get_handler(CreateUser)
assert handler.handle.called
```

### `get_session_stub`

Access the stub for a given session class. Each stub method records calls and lets you configure return values:

```python
stub = container.get_session_stub(MySession)
stub.is_dirty.returns(True)           # next call returns True
stub.is_dirty.always_returns(False)   # always returns False
stub.is_dirty.called                  # True if called at least once
stub.is_dirty.call_count              # number of calls
stub.is_dirty.calls                   # list of call argument lists
stub.begin.called                     # tracks begin() too
stub.commit.called                    # commit is called by the UseCase wrapper
```

### `get_port_stub`

Access the stub for a given port class. Works with any `Port` subclass:

```python
stub = container.get_port_stub(Logger)
stub.info.always_returns(None)
stub.info.called
stub.info.calls
```

### `get_handler`

Retrieve the handler for a given contract. Handler methods are also stubbed:

```python
handler = container.get_handler(CreateUser)
assert handler.handle.called
```

## `port_stub`

For testing ports outside a container context, create stubs directly:

```python
from aod.testing.doubles import port_stub

StubLogger = port_stub(Logger)
logger = StubLogger()
logger.info("test")
assert logger.info.called
```

Every public method on the port records calls and lets you configure return values:

```python
logger.info("message", user_id=1)
assert logger.info.called
assert logger.info.call_count == 1
entry = logger.info.calls[0]  # ["message", 1]
```

## Stub Control

Every stub method provides the same control interface:

| Method / Property | Signature | Description |
|-------------------|-----------|-------------|
| `returns` | `returns(*values: Any) -> None` | Set sequential return values (consumed FIFO) |
| `always_returns` | `always_returns(value: Any) -> None` | Set a constant return value for all calls |
| `called` | `property -> bool` | Whether the method was called at least once |
| `call_count` | `property -> int` | Number of times the method was called |
| `calls` | `property -> list[list[Any]]` | All recorded call arguments |

## Spy Classes

### SpyLogger

```python
from aod.testing.doubles import SpyLogger
```

`SpyLogger` is a ready-made implementation of `Logger(Port)`:

```python
logger = SpyLogger()
logger.info("order placed", order_id=1)
assert logger.info.called
```

### SpyEventBus

```python
from aod.testing.doubles import SpyEventBus
```

```python
bus = SpyEventBus()
bus.publish(OrderPlaced(order_id=1))
assert bus.publish.called
```

### SpyCache

```python
from aod.testing.doubles import SpyCache
```

```python
cache = SpyCache()
cache.get("key")
assert cache.get.called
```

### SpySession / SpyAsyncSession

```python
from aod.testing.doubles import SpySession, SpyAsyncSession
```

`SpySession` is a stub implementation of `Session` that records lifecycle calls:

```python
session = SpySession()
session.is_dirty.always_returns(False)
session.begin()
session.commit()
assert session.begin.called
assert session.commit.called
```

## FakeDomain

```python
from aod.testing import FakeDomain
```

`FakeDomain(Generic[T])` generates test data for domain objects using `polyfactory`.

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

```python
users = FakeDomain(User)
alice = users(name="Alice")  # auto-generates other fields
```

### `batch`

```python
def batch(self, count: int, overrides_list: list[dict[str, Any]] | None = None) -> list[T]
```

Build multiple instances.

```python
batch = users.batch(5)  # 5 users with auto-generated fields
```

## Common Testing Patterns

### Testing Use Cases with Spy Container

```python
from aod.testing.doubles import spy_adapter_container

class AppContainer(AdapterContainerBase):
    sessions: set = {MySession}
    handlers: list = [CreateUserHandler, GetUserHandler]

container = spy_adapter_container(AppContainer())
use_case = inject_adapters(container, CreateUserUseCase)
use_case.run(user_id=1, name="Alice")

assert_event_emitted(use_case.events, UserCreatedEvent, user_id=1)
assert container.get_handler(CreateUser).handle.called
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