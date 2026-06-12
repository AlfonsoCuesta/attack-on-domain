# Session

Sessions abstract database operations behind a uniform interface. They manage transactional boundaries and provide `execute`/`query` primitives for read and write operations.

## Session

```python
from aod.infrastructure import Session
```

`Session(Port)` is an abstract base class for synchronous database sessions.

### Constructor

`Session` has no constructor parameters. Subclasses define fields as needed.

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `execute` | `execute(self, operation: object) -> object` | Execute a write operation. Returns implementation-specific result. |
| `query` | `query(self, operation: object) -> object` | Execute a read operation. Returns implementation-specific result. |
| `begin` | `begin(self) -> None` | Start a new transaction. |
| `commit` | `commit(self) -> None` | Commit the current transaction. Raises `CommitOutsideUnitOfWorkError` if called outside a `UnitOfWork` context. |
| `rollback` | `rollback(self) -> None` | Roll back the current transaction. |
| `close` | `close(self) -> None` | Release session resources. |
| `is_dirty` | `is_dirty(self) -> bool` | Check whether uncommitted changes exist. |

#### Parameters

- **`operation: object`** — An object representing the database operation to perform. The type is implementation-specific (e.g., a SQL statement string, a statement object, a query builder).

## AsyncSession

```python
from aod.infrastructure import AsyncSession
```

`AsyncSession(Port)` is an abstract base class for asynchronous database sessions.

### Constructor

`AsyncSession` has no constructor parameters. Subclasses define fields as needed.

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `execute` | `async execute(self, operation: object) -> object` | Execute a write operation asynchronously. |
| `query` | `async query(self, operation: object) -> object` | Execute a read operation asynchronously. |
| `begin` | `async begin(self) -> None` | Start a new transaction asynchronously. |
| `commit` | `async commit(self) -> None` | Commit the current transaction. Raises `CommitOutsideUnitOfWorkError` if called outside a `UnitOfWork` context. |
| `rollback` | `async rollback(self) -> None` | Roll back the current transaction asynchronously. |
| `close` | `async close(self) -> None` | Release session resources asynchronously. |
| `is_dirty` | `is_dirty(self) -> bool` | Check whether uncommitted changes exist. This method is **sync** even on `AsyncSession`. |

#### Parameters

- **`operation: object`** — An object representing the database operation to perform. Type is implementation-specific.

## Transaction Pattern

Both `Session` and `AsyncSession` are designed to be used inside a `UnitOfWork` context. The `commit()` method is decorated to raise `CommitOutsideUnitOfWorkError` when called outside a `_CommitContext`.

```python
uow = container.get_uow()
uow.begin()
try:
    session.execute(operation)
    uow.commit()
except BaseException:
    uow.rollback()
    raise
finally:
    session.close()
```

## Testing with SpySession

```python
from aod.testing.doubles import SpySession, SpyAsyncSession
```

| Spy Class | Sync Methods | Async Methods |
|-----------|-------------|---------------|
| `SpySession` | `execute`, `query`, `begin`, `commit`, `rollback`, `close`, `is_dirty` | — |
| `SpyAsyncSession` | `is_dirty` | `execute`, `query`, `begin`, `commit`, `rollback`, `close` |

### Properties

- `SpySession.execute_calls` — `list[object]`, records each `execute()` call's operation argument.
- `SpySession.query_calls` — `list[object]`, records each `query()` call's operation argument.
- `SpySession.begin_calls`, `commit_calls`, `rollback_calls`, `close_calls` — `list[None]`, tracks lifecycle calls.
- `SpySession.set_dirty(dirty: bool)` — Set the dirty flag for `is_dirty()`.

## Common Patterns

### SQLAlchemy Implementation

```python
from aod.infrastructure import Session

class SqlAlchemySession(Session):
    connection: Connection

    def execute(self, operation: object) -> object:
        return self.connection.execute(operation)

    def query(self, operation: object) -> object:
        return self.connection.execute(operation)

    def begin(self) -> None:
        self.connection.begin()

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        self.connection.close()

    def is_dirty(self) -> bool:
        return self.connection.is_dirty()
```

### In-Memory Implementation

```python
from aod.infrastructure import Session

class InMemorySession(Session):
    _store: dict[str, Any] = Field(default_factory=dict)
    _dirty: bool = False

    def execute(self, operation: object) -> object:
        self._dirty = True
        ...

    def query(self, operation: object) -> object:
        ...

    def begin(self) -> None:
        pass

    def commit(self) -> None:
        self._dirty = False

    def rollback(self) -> None:
        self._store.clear()
        self._dirty = False

    def close(self) -> None:
        self._store.clear()

    def is_dirty(self) -> bool:
        return self._dirty
```

## Next Steps

- [Container: Wiring sessions into the dependency injection system](container.md)
- [Projections: Using sessions inside read/write projections](projections.md)
- [Testing Utilities: Testing with SpySession](../testing/index.md)