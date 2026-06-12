# Container

`AdapterContainerBase` wires dependencies for the application and infrastructure layers. It manages sessions, handlers, ports, and unit-of-work instances.

## AdapterContainerBase

```python
from aod.infrastructure import AdapterContainerBase
```

`AdapterContainerBase(BaseBehaviour)` is the base class for dependency injection containers.

### Constructor

`AdapterContainerBase(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `sessions` | `set[type[Session] \| type[AsyncSession]]` | Session classes (not instances) to manage. Default: `set()`. |
| `handlers` | `list[AnyHandler]` | Handler classes to register. Default: `[]`. |
| `logger` | `Logger \| AsyncLogger` | Logger instance. Default: `NullLogger`. |
| `event_bus` | `EventBus \| AsyncEventBus` | Event bus instance. Default: `NullEventBus`. |
| `cache` | `Cache \| AsyncCache` | Cache instance. Default: `NullCache`. |
| `**overrides` | `Any` | Override any field (ports, etc.). |

### Default Fields

| Field | Type | Default |
|-------|------|---------|
| `sessions` | `set[type[Session] \| type[AsyncSession]]` | `set()` |
| `_sessions_needed` | `dict[type[Session] \| type[AsyncSession], Session \| AsyncSession]` | `{}` (PrivateField) |
| `logger` | `Logger \| AsyncLogger` | `NullLogger()` |
| `event_bus` | `EventBus \| AsyncEventBus` | `NullEventBus()` |
| `cache` | `Cache \| AsyncCache` | `NullCache()` |
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

#### `get_port(port: type[Port]) -> Port`

Find a port implementation by type.

| Parameter | Type | Description |
|-----------|------|-------------|
| `port` | `type[Port]` | The port type to find. |

- Iterates container fields looking for one whose type is a subclass of the requested port.
- Returns the field value.
- Raises `PortNotFoundError` if no matching port is found.

#### `with_adapters(**overrides: Any) -> Self`

Create a copy of the container with overridden fields.

| Parameter | Type | Description |
|-----------|------|-------------|
| `**overrides` | `Any` | Field values to override in the copy. |

### Subclass Field Validation

When a subclass is created, all declared fields are validated:

- Fields must be `Port` subclasses (or `ClassVar` or inherited from `AdapterContainerBase`).
- Non-port fields raise `InvalidPortFieldError`.

### Handler Validation

The container enforces:

- No duplicate handler registrations (two handlers for the same contract raise `DuplicateHandlerError`).
- Each handler is inspected to determine which `Command` or `Query` type its `handle()` method accepts.

## Session Caching

Once a session is instantiated via `get_session()`, the same instance is returned on subsequent calls. This ensures all handlers and projections share the same session within a request.

## Multi-Session Support

The container supports both sync and async sessions simultaneously. `get_uow()` automatically detects the session type and returns the appropriate `UnitOfWork` or `AsyncUnitOfWork`.

## Testing with Spy Classes

```python
from aod.testing.doubles import SpySession, SpyLogger, SpyEventBus, SpyUnitOfWork

class MyContainer(AdapterContainerBase):
    pass

container = MyContainer(
    sessions={SpySession},
    logger=SpyLogger(),
    event_bus=SpyEventBus(),
)

session = container.get_session(SpySession)
uow = container.get_uow()
```

## Next Steps

- [Injection: Using inject_adapters to wire use cases](injection.md)
- [Projections: Using the container with projections](projections.md)
- [Sessions: Understanding session management](sessions.md)