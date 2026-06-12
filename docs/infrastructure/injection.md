# Injection

`inject_adapters()` wires dependencies from a container into use cases or projections, automatically resolving ports, sessions, and framework services.

## inject_adapters

```python
from aod.infrastructure import inject_adapters
```

### Function Signature

```python
def inject_adapters(
    container: AdapterContainerBase,
    operation_cls: type[UseCase | AsyncUseCase | ProjectionBase],
    **overrides: Any,
) -> UseCase | AsyncUseCase | ProjectionBase:
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `container` | `AdapterContainerBase` | The wired container instance providing logger, event_bus, cache, ports, and sessions. |
| `operation_cls` | `type[UseCase \| AsyncUseCase \| ProjectionBase]` | The class to inject dependencies into. Can be a UseCase, AsyncUseCase, or any ProjectionBase subclass. |
| `**overrides` | `Any` | Optional field overrides. When provided, the container is copied with these overrides before injection. |

### Returns

An instance of `operation_cls` with all dependencies wired.

## Auto-Wiring Logic

### Framework Services

All operations receive these from the container:

| Field | Container Source |
|-------|-----------------|
| `logger` | `container.logger` |
| `event_bus` | `container.event_bus` |
| `cache` | `container.cache` |

### Use Case Wiring

When `operation_cls` is a `UseCase` or `AsyncUseCase`:

| Field | Source |
|-------|--------|
| `uow` | `container.get_uow()` |

### Projection Wiring

When `operation_cls` is a `ProjectionBase` subclass:

| Field | Source |
|-------|--------|
| `session` | `container.get_session(session_type)` |

The session type is extracted from the projection's `session` field annotation. If the field type is `None`, `session` is set to `None`.

### Port Wiring

All non-framework fields are scanned:

1. Each field's type is checked against all registered ports via `container.get_port()`.
2. `HandlerProtocol` subclasses are excluded (not injected as ports).
3. Special types (`UnitOfWork`, `Logger`, `EventBus`, `Cache`, and their async counterparts) are skipped — they are handled separately above.

### Override Support

```python
use_case = inject_adapters(
    container,
    MyUseCase,
    logger=SpyLogger(),  # override logger for testing
)
```

When `**overrides` are provided:

1. `container.copy(**overrides)` creates a temporary container with overridden fields.
2. Injection proceeds using the overridden container.

## Async Use Case Injection

Async use cases are wired identically to sync use cases:

```python
from aod.application.async_ import UseCase

class MyAsyncUseCase(UseCase):
    ...

use_case = inject_adapters(container, MyAsyncUseCase)
assert isinstance(use_case.uow, AsyncUnitOfWork)
```

## Common Patterns

### Manual Injection

```python
container = MyContainer(
    sessions={MySession},
    handlers=[MyHandler],
    user_client=MyUserClient(),
)

use_case = inject_adapters(container, CreateUser)
use_case.run(user_id=42, name="Alice")
```

### Testing with Overrides

```python
from aod.testing.doubles import SpyLogger, SpyEventBus, SpyUnitOfWork

container = MyContainer()

use_case = inject_adapters(
    container,
    CreateUser,
    logger=SpyLogger(),
    event_bus=SpyEventBus(),
    uow=SpyUnitOfWork(),
)

use_case.run(user_id=42, name="Alice")
assert use_case.uow.committed
```

### Projection Injection

```python
class UserProjection(ReadProjection):
    session: Session | None = None

    def read(self, model: ReadModel) -> list[User]:
        return self.session.query("SELECT * FROM users")

container = MyContainer(sessions={MySession})
proj = inject_adapters(container, UserProjection)
result = proj.read(ReadModel())
```

## Next Steps

- [Container: Understanding the dependency injection container](container.md)
- [Projections: Working with read/write projections](projections.md)
- [Testing Utilities: Testing with spy classes](../testing/index.md)