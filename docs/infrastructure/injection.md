# Injection

The container provides two methods for wiring dependencies: `adapt_use_case()` for use cases and `adapt_projection()` for projections. Both resolve ports, sessions, and framework services automatically.

## adapt_use_case

```python
container.adapt_use_case(use_case_cls, **overrides)
```

Wire dependencies from a container into a use case.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `use_case_cls` | `type[UseCase \| AsyncUseCase]` | The use case class to inject dependencies into. |
| `**overrides` | `Any` | Optional field overrides. When provided, the container is copied with these overrides before injection. |

### Returns

An instance of `use_case_cls` with all dependencies wired.

## adapt_projection

```python
container.adapt_projection(projection_cls, **overrides)
```

Wire dependencies from a container into a projection.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `projection_cls` | `type[ProjectionBase]` | The projection class to inject dependencies into. |
| `**overrides` | `Any` | Optional field overrides. When provided, the container is copied with these overrides before injection. |

### Returns

An instance of `projection_cls` with all dependencies wired.

## Auto-Wiring Logic

### Framework Services

All operations receive these from the container:

| Field | Container Source |
|-------|-----------------|
| `logger` | `container.logger` |
| `event_bus` | `container.event_bus` |
| `cache` | `container.cache` |

### Use Case Wiring

When adapting a `UseCase` or `AsyncUseCase`:

| Field | Source |
|-------|--------|
| `uow` | `container.get_uow()` |

### Projection Wiring

When adapting a `ProjectionBase` subclass:

| Field | Source |
|-------|--------|
| `session` | `container.get_session(session_type)` |

The session type is extracted from the projection's `session` field annotation. If the field type is `None`, `session` is set to `None`.

### Port Wiring

All non-framework fields are scanned:

1. Each field's type is checked against all registered ports via `container.get_port()`.
2. `HandlerProtocol` subclasses are excluded (not injected as ports).
3. Special types (`UnitOfWork`, `Logger`, `EventBus`, `Cache`, and their async counterparts) are skipped -- they are handled separately above.

### Override Support

```python
use_case = container.adapt_use_case(
    MyUseCase,
    logger=SpyLogger(),  # override logger for testing
)
```

When `**overrides` are provided:

1. `container.with_adapters(**overrides)` creates a temporary container with overridden fields.
2. Injection proceeds using the overridden container.

## Async Use Case Injection

Async use cases are wired identically to sync use cases:

```python
from aod.application.async_ import UseCase

class MyAsyncUseCase(UseCase):
    ...

use_case = container.adapt_use_case(MyAsyncUseCase)
assert isinstance(use_case.uow, AsyncUnitOfWork)
```

## Common Patterns

### Manual Injection

```python
container = AppContainer(
    sessions={MySession},
    handlers=[MyHandler],
    user_client=MyUserClient(),
)

use_case = container.adapt_use_case(CreateUser)
use_case.run(user_id=42, name="Alice")
```

### Testing with Spy Container

```python
from aod.testing.doubles import spy_adapter_container

container = spy_adapter_container(AppContainer())

use_case = container.adapt_use_case(CreateUserUseCase)
use_case.run(user_id=42, name="Alice")

assert container.get_handler(CreateUser).handle.called

use_case.run(user_id=42, name="Alice")
assert use_case.uow.committed
```

### Projection Injection

```python
class UserProjection(ReadProjection):
    session: Session | None = None

    def read(self, model: ReadModel) -> list[User]:
        return self.session.query("SELECT * FROM users")

container = AppContainer(sessions={MySession})
proj = container.adapt_projection(UserProjection)
result = proj.read(ReadModel())
```

## Next Steps

<div class="home-features">

</div>
