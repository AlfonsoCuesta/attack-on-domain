# Container

`AdapterContainer` wires dependencies for the application and infrastructure layers. It manages sessions, handlers (`CommandHandler[C]`, `QueryHandler[Q]`), ports, and unit-of-work instances. Handlers implement `CommandPort[C]` / `QueryPort[Q]` and are injected into UseCase fields automatically.

## AdapterContainer

```python
from aod.infrastructure import AdapterContainer
```

`AdapterContainer` is the dependency injection container. It can be used directly without subclassing, or subclassed to declare custom ports.

### Constructor

`AdapterContainer(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `sessions` | `set[type[Session] \| type[AsyncSession]]` | Session classes (not instances) to manage. Default: `set()`. |
| `handlers` | `list[AnyHandler]` | Handler classes to register. Default: `[]`. |
| `ports` | `dict[type[Port], Port]` | Type-based port resolution fallback. When a port field type is not found by name, the container checks this dict. Default: `{}`. |
| `**fields` | `Port` | Custom ports registered by field name. Any keyword argument that is a `Port` instance is registered by name. |

### Default Fields

| Field | Type | Default |
|-------|------|---------|
| `sessions` | `set[type[Session] \| type[AsyncSession]]` | `set()` |
| `handlers` | `list[AnyHandler]` | `[]` |
| `ports` | `dict[type[Port], Port]` | `{}` |
| `_ports_by_name` | `dict[str, Port]` | `{}` (PrivateField) |
| `_sessions_needed` | `dict[type[Session] \| type[AsyncSession], Session \| AsyncSession]` | `{}` (PrivateField) |

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

#### `adapt(operation_cls: type[TOperation], **overrides: Any) -> TOperation`

Create a use case or projection instance with all dependencies wired automatically. This is the single public entry point for dependency injection — it dispatches to the appropriate internal method based on the class type.

| Parameter | Type | Description |
|-----------|------|-------------|
| `operation_cls` | `type[UseCase \| AsyncUseCase \| ProjectionBase]` | The use case or projection class to instantiate. |
| `**overrides` | `Any` | Optional field overrides for the container copy. |

For use cases:
- Resolves `uow` automatically.
- Injects matching handler ports (`CommandPort[C]`, `QueryPort[Q]`) by contract type.
- Injects custom ports by field name, with type-based fallback from `ports` dict.

For projections:
- Injects sessions by type annotation for any field with a `Session`/`AsyncSession` annotation.
- Injects custom ports by field name, with type-based fallback from `ports` dict.

When `**overrides` are provided, creates a container copy before injection.

#### `with_adapters(**overrides: Any) -> Self`

Create a copy of the container with overridden fields.

| Parameter | Type | Description |
|-----------|------|-------------|
| `**overrides` | `Any` | Field values to override in the copy. |

### Port Resolution Order

When injecting ports into a use case or projection, the container resolves each port field in this order:

1. **Named port** — looks up the field name in `_ports_by_name` (from container subclass fields or keyword arguments).
2. **Type-based fallback** — looks up the field's type annotation in `self.ports` dict.
3. If neither resolves, raises `PortNotFoundError`.

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
| `CommandPort[C]` / `QueryPort[Q]` | `container.get_handler(contract_type)` |
| Custom ports | Named ports or `ports` dict (see Port Resolution Order) |

### Projection Wiring

When adapting a `ProjectionBase` subclass:

| Field | Source |
|-------|--------|
| Session fields | `container.get_session(session_type)` for each field with a `Session`/`AsyncSession` type annotation |
| Custom ports | Named ports or `ports` dict (see Port Resolution Order) |

Projections do not have a default `session` field. Each session must be declared as a concrete type annotation (e.g., `session: PostgresSession`). Multiple session fields are supported.

### Override Support

```python
container = AdapterContainer(sessions={MySession}, handlers=[MyHandler])

use_case = container.adapt(
    MyUseCase,
    logger=SpyLogger(),  # override for testing
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

use_case = container.adapt(MyAsyncUseCase)
assert isinstance(use_case.uow, AsyncUnitOfWork)
```

## Common Patterns

### Base Container (No Subclassing)

```python
container = AdapterContainer(
    sessions={MySession},
    handlers=[MyHandler],
    ports={Logger: SpyLogger()},
    user_client=MyUserClient(),
)

use_case = container.adapt(CreateUser)
use_case.run(user_id=42, name="Alice")
```

### Subclassed Container

```python
class AppContainer(AdapterContainer):
    logger: Logger

container = AppContainer(
    sessions={MySession},
    handlers=[MyHandler],
    logger=SpyLogger(),
)

use_case = container.adapt(CreateUser)
```

### Testing with Spy Container

```python
from aod.testing.doubles import spy_adapter_container

container = spy_adapter_container(AdapterContainer(sessions={MySession}, handlers=[CreateUserHandler]))

container.get_handler_stub(CreateUserHandler).handle.returns(None)

# Spy container has adapt_use_case/adapt_projection with returns/read_returns/write_returns
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
    session: MySession

    def read(self, model: ReadModel) -> list[User]:
        return self.session.query("SELECT * FROM users")

container = AdapterContainer(sessions={MySession})
proj = container.adapt(UserProjection)
result = proj.read(ReadModel())
```

## Next Steps

<div class="home-features">

</div>