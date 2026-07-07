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
from aod.application import Logger
from aod.infrastructure import AdapterContainer
from aod.testing.doubles import spy_adapter_container


container = spy_adapter_container(
    AdapterContainer(
        sessions={MySession},
        handlers=[CreateUserHandler, GetUserHandler],
        logger=SpyLogger(),
    )
)

# Configure session behavior
container.get_session_stub(MySession).is_dirty.return_value = True
container.get_session_stub(MySession).begin.return_value = None

# Configure port behavior (optional)
container.get_port_stub("logger").info.return_value = None

# Configure handler stub
container.get_handler_stub(CreateUserHandler).handle.return_value = None

# Configure and inject
container.stub_use_case(CreateUserUseCase, returns=None)
use_case = container.adapt(CreateUserUseCase)
use_case.run(user_id=1, name="Alice")

# Assert handler was called
handler = container.get_handler(CreateUser)
assert handler.handle.called
```

### `get_session_stub`

Access the stub for a given session class. Each stub method records calls and lets you configure return values:

```python
stub = container.get_session_stub(MySession)
stub.is_dirty.return_value = True      # always returns True
stub.is_dirty.side_effect = [True, False]  # first True, then False
stub.is_dirty.called                  # True if called at least once
stub.is_dirty.call_count              # number of calls
stub.is_dirty.call_args_list          # list of call objects, each with .args and .kwargs
stub.begin.called                     # tracks begin() too
stub.commit.called                    # commit is called by the UseCase wrapper
```

### `get_port_stub`

Access the stub for a given port field name. Works with any `Port` subclass registered on the container:

```python
container = spy_adapter_container(AdapterContainer(logger=SpyLogger()))
stub = container.get_port_stub("logger")
stub.info.return_value = None
stub.info.called
stub.info.call_args_list
```

### `get_handler`

Retrieve the handler for a given contract. Handler methods are also stubbed:

```python
handler = container.get_handler(CreateUser)
assert handler.handle.called
```

### `get_handler_stub`

Access the handler stub for a given handler class. Works like `get_port_stub` for handlers:

```python
stub = container.get_handler_stub(CreateUserHandler)
stub.handle.return_value = None
stub.handle.called
```

### `stub_use_case` with `returns=` / `raises=`

Configure a use case stub before calling `adapt`. `returns=` stubs `instance.run` to return the given value; `raises=` makes it raise an exception:

```python
container.stub_use_case(CreateUserUseCase, returns=42)
use_case = container.adapt(CreateUserUseCase)
result = use_case.run(user_id=1)  # returns 42
```

### `stub_projection` with `read_returns` / `read_raises` / `write_returns` / `write_raises`

Configure a projection stub before calling `adapt`:

```python
container.stub_projection(MyProjection, read_returns=[], write_returns=None)
proj = container.adapt(MyProjection)
proj.read(model)    # returns []
proj.write(model)   # returns None
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

Every stub method is a `unittest.mock.MagicMock` or `AsyncMock`. Configure return values and inspect calls with the standard mock API:

```python
logger.info("message", user_id=1)
assert logger.info.called
assert logger.info.call_count == 1
entry = logger.info.call_args_list[0]
entry.args    # ("message",)
entry.kwargs  # {"user_id": 1}
```

## Stub Control

Every stub method is a `unittest.mock` mock object:

| Property / Method | Description |
|-------------------|-------------|
| `.return_value = value` | Always return this value |
| `.side_effect = exc` | Raise an exception |
| `.side_effect = [v1, v2]` | Return different values on successive calls |
| `.called` | Whether the method was called |
| `.call_count` | Number of calls |
| `.call_args_list` | List of `call` objects — each has `.args` and `.kwargs` |

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
session.is_dirty.return_value = False
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


container = spy_adapter_container(AdapterContainer(sessions={MySession}, handlers=[CreateUserHandler, GetUserHandler]))
use_case = container.adapt(CreateUserUseCase)
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

<div class="home-features">

</div>