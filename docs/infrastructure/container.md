# Container

`AdapterContainer` wires dependencies for the application and infrastructure layers. It manages sessions, handlers (`CommandHandler[C]`, `QueryHandler[Q]`), ports, and unit-of-work instances. Handlers implement `CommandPort[C]` / `QueryPort[Q]` and are injected into UseCase fields automatically.

## AdapterContainer

```python
from aod.infrastructure import AdapterContainer
```

`AdapterContainer` is the dependency injection container.

### Constructor

`AdapterContainer(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `sessions` | `set[type[Session] \| type[AsyncSession]]` | Session classes (not instances) to manage. Default: `set()`. |
| `handlers` | `list[AnyHandler]` | Handler classes to register. Default: `[]`. |
| `**fields` | `Port` | Custom ports registered by field name. |

### Default Fields

| Field | Type | Default |
|-------|------|---------|
| `sessions` | `set[type[Session] \| type[AsyncSession]]` | `set()` |
| `_sessions_needed` | `dict[type[Session] \| type[AsyncSession], Session \| AsyncSession]` | `{}` (PrivateField) |
| `_ports_by_name` | `dict[str, Port]` | `{}` (PrivateField) |
| `handlers` | `list[AnyHandler]` | `[]` |

### Methods

#### `__post_init__(self) -> None`

Called after construction. Validates that no duplicate handlers are registered.

#### `get_session(session_cls: type[Session] | type[AsyncSession]) -> Session | AsyncSession`

Retrieve or instantiate a session class.

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_cls` | `type[Session] \| type[AsyncSession]` | The session class to retrieve. |

- If the session class has already been instantiated, returns the cached instance.
- Otherwise, finds a matching class in `self.sessions`, instantiates it, caches it in `_sessions_needed`, and returns it.
- Raises `SessionNotFoundError` if no matching session class is registered.

#### `get_handler(contract: type[Command] | type[Query]) -> CommandHandler | AsyncCommandHandler | QueryHandler | AsyncQueryHandler`

Find and instantiate a handler for a given contract.

| Parameter | Type | Description |
|-----------|------|-------------|
| `contract` | `type[Command] \| type[Query]` | The command or query class. |

- Searches registered handlers for one whose `handle()` method accepts the given contract.
- Resolves the handler's `session` field type and retrieves the matching session.
- Raises `HandlerNotFoundError` if no handler matches the contract.
- Raises `HandlerModelError` if the handler is missing a `session` field.

#### `get_uow() -> UnitOfWork | AsyncUnitOfWork`

Create a unit-of-work with all sessions that have been instantiated.

- Collects all session instances from `_sessions_needed`.
- Returns `AsyncUnitOfWork` if any session is async, otherwise `UnitOfWork`.

#### `get_port(name: str) -> Port`

Find a port implementation by field name.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | The field name registered on the container. |

- Looks up `_ports_by_name` for the registered field name.
- Returns the field value.
- Raises `PortNotFoundError` if no port with that name is found.

#### `adapt_use_case(use_case_cls: type[UseCase | AsyncUseCase], **overrides: Any) -> UseCase | AsyncUseCase`

Create a use case instance with all dependencies wired automatically.

| Parameter | Type | Description |
|-----------|------|-------------|
| `use_case_cls` | `type[UseCase \| AsyncUseCase]` | The use case class to instantiate. |
| `**overrides` | `Any` | Optional field overrides for the container copy. |

- Resolves `uow` automatically.
- Injects matching handler ports (`CommandPort[C]`, `QueryPort[Q]`) and custom ports by field name.
- Injects `Logger`, `EventBus`, `Cache` and other ports by field name.
- When `**overrides` are provided, creates a container copy before injection.

#### `adapt_projection(projection_cls: type[ProjectionBase], **overrides: Any) -> ProjectionBase`

Create a projection instance with all dependencies wired automatically.

| Parameter | Type | Description |
|-----------|------|-------------|
| `projection_cls` | `type[ProjectionBase]` | The projection class to instantiate. |
| `**overrides` | `Any` | Optional field overrides for the container copy. |

- Resolves `session` automatically.
- The session type is extracted from the projection's `session` field annotation.
- Injects matching custom ports by field name.
- When `**overrides` are provided, creates a container copy before injection.

#### `with_adapters(**overrides: Any) -> Self`

Create a copy of the container with overridden fields.

| Parameter | Type | Description |
|-----------|------|-------------|
| `**overrides` | `Any` | Field values to override in the copy. |

### Subclass Field Validation

When a subclass is created, all declared fields are validated:

- Fields must be `Port` subclasses (or `ClassVar` or inherited from `AdapterContainer`).
- Non-port fields raise `InvalidPortFieldError`.

### Handler Validation

The container enforces:

- No duplicate handler registrations (two handlers for the same contract raise `DuplicateHandlerError`).
- Each handler is inspected to determine which `Command` or `Query` type its `handle()` method accepts.

## Session Caching

Once a session is instantiated via `get_session()`, the same instance is returned on subsequent calls. This ensures all handlers and projections share the same session within a request.

## Multi-Session Support

The container supports both sync and async sessions simultaneously. `get_uow()` automatically detects the session type and returns the appropriate `UnitOfWork` or `AsyncUnitOfWork`.

## Auto-Wiring Logic

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

All public fields are scanned:

1. Each field's name is looked up in `_ports_by_name`.
2. `HandlerProtocol` subclasses are excluded (not injected as ports).
3. If the field name is not registered, `PortNotFoundError` is raised.

This applies to custom ports as well as `Logger`, `EventBus`, `Cache` and their async counterparts.

### Override Support

```python
class MyContainer(AdapterContainer):
    logger: Logger

use_case = container.adapt_use_case(
    MyUseCase,
    logger=SpyLogger(),  # override container field for testing
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
container = AdapterContainer(
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

container = spy_adapter_container(AdapterContainer())

container.get_handler_stub(CreateUserHandler).handle.returns(None)

use_case = container.adapt_use_case(CreateUserUseCase, returns=None)
use_case.run(user_id=42, name="Alice")

assert container.get_handler(CreateUser).handle.called
assert container.get_handler_stub(CreateUserHandler).handle.call_count == 1

# Projection stubs
proj = container.adapt_projection(UserProjection, read_returns=[])
result = proj.read(model)  # returns []
```

### Projection Injection

```python
class UserProjection(ReadProjection):
    def read(self, model: ReadModel) -> list[User]:
        return self.session.query("SELECT * FROM users")

container = AdapterContainer(sessions={MySession})
proj = container.adapt_projection(UserProjection)
result = proj.read(ReadModel())
```

## Next Steps

<div class="home-features">

</div>