# Testing Utilities

Testing helpers and doubles for building tests with the framework.

## Import Paths

All testing utilities are accessible via `aod.testing`:

```python
from aod.testing import FakeDomain, build, events_of
from aod.testing import assert_event_emitted, assert_no_events, check_invariant
from aod.testing.doubles.application import LogEntry, SpyLogger, SpyEventBus, SpyUnitOfWork
from aod.testing.doubles.application.async_ import SpyLogger, SpyEventBus, SpyUnitOfWork
```

Async doubles are re-exported with the same names as their sync counterparts (without the `Async` prefix). The context (`async_` package) disambiguates which one you get.

## Helpers

### `build(cls, **kwargs)`

Constructs a domain object bypassing validation (uses the raw Pydantic model). Useful in tests when you need to create a valid instance without satisfying all validation rules:

```python
from aod.testing import build

user = build(User, id=1, name="Alice")
```

### `events_of(obj)`

Extracts all events emitted by an entity, value object, or service:

```python
from aod.testing import events_of

user = User(id=1)
events = events_of(user)  # list[Event]
```

### `assert_event_emitted(events, event_type, **attrs)`

Asserts that a specific event type with matching attributes exists in a list of events. Returns the matching event:

```python
from aod.testing import assert_event_emitted

events = events_of(user)
e = assert_event_emitted(events, UserCreated, user_id=1)
```

Raises `AssertionError` if no event matches.

### `assert_no_events(events)`

Asserts that a list of events is empty:

```python
from aod.testing import assert_no_events

assert_no_events(events_of(user))
```

### `check_invariant(cls, name, **data)`

Runs a single invariant validator on an instance built from `**data`. Useful for testing specific validation logic:

```python
from aod.testing import check_invariant

check_invariant(User, "adult", username="Alice", age=20)  # passes
check_invariant(User, "adult", username="Alice", age=15)  # raises InvarianceException
```

## FakeDomain

Generates domain objects with auto-filled fake data for fields not explicitly provided:

```python
from aod.testing import FakeDomain
from aod.domain import RootEntity

class User(RootEntity):
    id: int
    name: str
    email: str

UserFactory = FakeDomain(User)
user = UserFactory(id=1)  # name and email are auto-generated
```

Supports nested value objects, batches, and defaults:

```python
UserFactory = FakeDomain(User, name="Alice")
users = UserFactory.batch(3, [{"id": 1}, {"id": 2}, {"id": 3}])
```

## Test Doubles

### Sync Doubles

```python
from aod.testing.doubles.application import SpyLogger, SpyEventBus, SpyUnitOfWork

log = SpyLogger()
log.info("hello", user_id=42)
assert len(log.entries) == 1

bus = SpyEventBus()
bus.publish(event)
assert len(bus.published) == 1

uow = SpyUnitOfWork()
uow.set_dirty()
uow.commit()
assert uow.committed
assert uow.flushed  # SpyUnitOfWork.flush is a no-op by default
```

### Async Doubles

```python
from aod.testing.doubles.application.async_ import SpyLogger, SpyEventBus, SpyUnitOfWork

log = SpyLogger()
await log.info("hello")
assert len(log.entries) == 1

bus = SpyEventBus()
await bus.publish(event)
assert len(bus.published) == 1

uow = SpyUnitOfWork()
uow.set_dirty()
await uow.commit()
assert uow.committed
```
