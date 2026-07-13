# Projections

Projections provide a structured way to read and write data efficiently. They handle event collection, logging, event bus publishing, and transactional commit/rollback automatically.

## Data Models



```python
from pydantic import BaseModel

class UserSearch(BaseModel):
    query: str
    page: int = 1

class UserUpdate(BaseModel):
    user_id: str
    name: str
    email: str
```


## ReadProjection

```python
from aod.infrastructure import ReadProjection
```

`ReadProjection(ReadProjectionBase)` — Base class for synchronous read projections.

### Constructor

`ReadProjection(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `**fields` | `Port \| Session` | Field dependencies. Includes optional session fields (concrete type, e.g. `session: PostgresSession`) and port dependencies. All fields (except sessions) must be `Port` subclasses. |

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `read` | `read(self, *args, **kwargs) -> Any` | Abstract. Execute a read operation. Auto-wrapped with `EventCollector`, logging, and event bus publish. |

#### `read` Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `*args` | `Any` | Positional arguments for the read operation. |
| `**kwargs` | `Any` | Keyword arguments for the read operation. |

#### Auto-Wrapping Behavior

When `read()` is called:

1. Events are collected via `EventCollector` during execution.
2. On success: events are logged on each declared logger, events are published on each declared event bus.
3. On failure: the exception is logged on each declared logger and re-raised.

### Example

```python
from pydantic import BaseModel
from aod.infrastructure import ReadProjection

class UserSearch(BaseModel):
    user_id: str

class UserListProjection(ReadProjection):
    session: PostgresSession

    def read(self, model: UserSearch) -> list[User]:
        rows = self.session.query(
            "SELECT * FROM users WHERE id = :id",
            {"id": model.user_id},
        )
        return [User(**row) for row in rows]
```

## WriteProjection

```python
from aod.infrastructure import WriteProjection
```

`WriteProjection(WriteProjectionBase)` — Base class for synchronous write projections.

### Constructor

`WriteProjection(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `**fields` | `Port \| Session` | Field dependencies. Includes optional session fields (concrete type, e.g. `session: PostgresSession`) and port dependencies. All fields (except sessions) must be `Port` subclasses. |

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `write` | `write(self, *args, **kwargs) -> Any` | Abstract. Execute a write operation. Auto-wrapped with `CommitContext`, `EventCollector`, logging, rollback, and event bus publish. |

#### `write` Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `*args` | `Any` | Positional arguments for the write operation. |
| `**kwargs` | `Any` | Keyword arguments for the write operation. |

#### Auto-Wrapping Behavior

When `write()` is called:

1. A `CommitContext` is set (enabling `session.commit()`).
2. Events are collected via `EventCollector` during execution.
3. On success: events are logged on each declared logger, events are published on each declared event bus.
5. On failure: `session.rollback()` is called (if session is dirty), the exception is logged on each declared logger and re-raised.
6. The `CommitContext` is always reset in the `finally` block.

### Example

```python
from pydantic import BaseModel
from aod.infrastructure import WriteProjection

class UpdateUserInput(BaseModel):
    user_id: str
    name: str

class UserUpdateProjection(WriteProjection):
    session: PostgresSession

    def write(self, model: UpdateUserInput) -> None:
        self.session.execute(
            "UPDATE users SET name = :name WHERE id = :id",
            {"name": model.name, "id": model.user_id},
        )
```

## Projection

```python
from aod.infrastructure import Projection
```

`Projection(ReadProjection, WriteProjection)` — Combines both read and write capabilities.

### Constructor

`Projection(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `**fields` | `Port \| Session` | Field dependencies. Includes optional session fields (concrete type, e.g. `session: PostgresSession`) and port dependencies. All fields (except sessions) must be `Port` subclasses. |

### Methods

Includes both `read(self, model: Any) -> Any` and `write(self, model: Any) -> Any`.

## Async Variants

| Class | Import | Base |
|-------|--------|------|
| `AsyncReadProjection` | `from aod.infrastructure import AsyncReadProjection` | `AsyncReadProjectionBase` |
| `AsyncWriteProjection` | `from aod.infrastructure import AsyncWriteProjection` | `AsyncWriteProjectionBase` |
| `AsyncProjection` | `from aod.infrastructure import AsyncProjection` | `AsyncReadProjection + AsyncWriteProjection` |

### Constructor

Async variants accept the same fields as their sync counterparts. Session fields must use concrete types (e.g., `session: AsyncPostgresSession`). Multiple session fields are supported.

All async variants expose the same methods but as `async`:
- `async read(self, *args, **kwargs) -> Any`
- `async write(self, *args, **kwargs) -> Any`

## Field Validation

Projections enforce these rules at class creation time:

1. **Concrete session types** — Session fields must use concrete types (e.g., `session: PostgresSession`), never `Session | None`.
2. **No HandlerProtocol** — Fields typed as `HandlerProtocol` or its subclasses raise `InvalidUseCasePortFieldError`.
3. **Multiple sessions allowed** — Projections can declare multiple session fields with different types.
4. **No HandlerProtocol** — Fields typed as `HandlerProtocol` or its subclasses raise `InvalidUseCasePortFieldError`.

## Event Collection

Events emitted during `read()` or `write()` are automatically collected:

- Collected events are stored on `self.events` after execution completes.
- Events are published on the event bus after a successful operation.
- Write projections require a successful commit before events are published.

## Testing with SpySession

```python
from aod.testing.doubles import SpySession
from pydantic import BaseModel

class UserSearch(BaseModel):
    user_id: int

class MyReadProjection(ReadProjection):
    def read(self, model: UserSearch) -> Any:
        result = self.session.query("SELECT * FROM users")
        ...

class MyReadProjection(ReadProjection):
    session: SpySession

    def read(self, model: UserSearch) -> Any:
        ...

proj = MyReadProjection(session=SpySession())
result = proj.read(UserSearch(user_id=42))
assert proj.session.is_dirty.called
```

## Next Steps

<div class="home-features">

</div>
