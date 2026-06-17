# Projections

Projections provide a structured way to read and write data efficiently. They handle event collection, logging, event bus publishing, and transactional commit/rollback automatically.

## Data Models

```python
from aod.infrastructure import ReadModel, WriteModel
```

### ReadModel

`ReadModel` — An immutable input model for read projections. Fields can reference any type.

#### Constructor

`ReadModel(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `**fields` | `Any` | Keyword arguments matching declared fields. All fields are required unless they have defaults. |

### WriteModel

`WriteModel` — An immutable input model for write projections. Fields can reference any type.

#### Constructor

`WriteModel(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `**fields` | `Any` | Keyword arguments matching declared fields. All fields are required unless they have defaults. |

## ReadProjection

```python
from aod.infrastructure import ReadProjection
```

`ReadProjection(ReadProjectionBase)` — Base class for synchronous read projections.

### Constructor

`ReadProjection(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `session` | `Session \| None` | Optional database session. Default: `None`. |
| `**ports` | `Port` | Additional port dependencies. All fields (except `session`) must be `Port` subclasses. |

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `read` | `read(self, model: ReadModel) -> Any` | Abstract. Execute a read operation. Auto-wrapped with `EventCollector`, logging, and event bus publish. |

#### `read` Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | `ReadModel` | The input data model for the read operation. |

#### Auto-Wrapping Behavior

When `read()` is called:

1. Events are collected via `EventCollector` during execution.
2. On success: events are logged, cache is flushed, events are published on the event bus.
3. On failure: the exception is logged and re-raised.

## WriteProjection

```python
from aod.infrastructure import WriteProjection
```

`WriteProjection(WriteProjectionBase)` — Base class for synchronous write projections.

### Constructor

`WriteProjection(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `session` | `Session \| None` | Optional database session. Default: `None`. |
| `**ports` | `Port` | Additional port dependencies. All fields (except `session`) must be `Port` subclasses. |

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `write` | `write(self, model: WriteModel) -> Any` | Abstract. Execute a write operation. Auto-wrapped with `CommitContext`, `EventCollector`, logging, rollback, and event bus publish. |

#### `write` Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | `WriteModel` | The input data model for the write operation. |

#### Auto-Wrapping Behavior

When `write()` is called:

1. A `CommitContext` is set (enabling `session.commit()`).
2. If a session is configured, `session.begin()` is called.
3. Events are collected via `EventCollector` during execution.
4. On success: events are logged, cache is flushed, events are published on the event bus.
5. On failure: `session.rollback()` is called (if session is dirty), the exception is logged and re-raised.
6. The `CommitContext` is always reset in the `finally` block.

## Projection

```python
from aod.infrastructure import Projection
```

`Projection(ReadProjection, WriteProjection)` — Combines both read and write capabilities.

### Constructor

`Projection(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `session` | `Session \| None` | Optional database session. Default: `None`. |
| `**ports` | `Port` | Additional port dependencies. All fields (except `session`) must be `Port` subclasses. |

### Methods

Includes both `read(self, model: ReadModel) -> Any` and `write(self, model: WriteModel) -> Any`.

## Async Variants

| Class | Import | Base |
|-------|--------|------|
| `AsyncReadProjection` | `from aod.infrastructure import AsyncReadProjection` | `AsyncReadProjectionBase` |
| `AsyncWriteProjection` | `from aod.infrastructure import AsyncWriteProjection` | `AsyncWriteProjectionBase` |
| `AsyncProjection` | `from aod.infrastructure import AsyncProjection` | `AsyncReadProjection + AsyncWriteProjection` |

### Constructor Differences

- `AsyncReadProjection`: `session: Session | AsyncSession | None = None`
- `AsyncWriteProjection`: `session: Session | AsyncSession | None = None`
- `AsyncProjection`: `session: Session | AsyncSession | None = None`

All async variants expose the same methods but as `async`:
- `async read(self, model: ReadModel) -> Any`
- `async write(self, model: WriteModel) -> Any`

## Field Validation

Projections enforce these rules at class creation time:

1. **Port subclasses only** — All fields must be `Port` subclasses (except `session`).
2. **Max one Session** — At most one field of type `Session` or `AsyncSession` is allowed. A second session field raises `InvalidPortFieldError`.
3. **No HandlerProtocol** — Fields typed as `HandlerProtocol` or its subclasses raise `InvalidUseCasePortFieldError`.

## Event Collection

Events emitted during `read()` or `write()` are automatically collected:

- Collected events are stored on `self.events` after execution completes.
- Events are published on the event bus after a successful operation.
- Write projections require a successful commit before events are published.

## Testing with SpySession

```python
from aod.testing.doubles import SpySession

class MyReadProjection(ReadProjection):
    session: Session | None = None

    def read(self, model: ReadModel) -> Any:
        result = self.session.query("SELECT * FROM users")
        ...

proj = MyReadProjection(session=SpySession())
result = proj.read(ReadModel())
assert proj.session.is_dirty.called
```

## Next Steps

- [Sessions: Understanding the database abstraction](sessions.md)
- [Container: Wiring projections into the dependency injection system](container.md)
- [Injection: Using inject_adapters with projections](injection.md)