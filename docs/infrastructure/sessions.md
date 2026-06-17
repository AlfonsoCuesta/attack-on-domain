# Session

Sessions abstract database operations behind a uniform interface. They manage transactional boundaries and define a minimal set of required lifecycle methods.

## Session

```python
from aod.infrastructure import Session
```

`Session(Port)` is an abstract base class for synchronous database sessions.

### Required Methods

Subclasses **must** implement these abstract methods:

| Method | Signature | Description |
|--------|-----------|-------------|
| `begin` | `begin(self) -> None` | Start a new transaction. |
| `commit` | `commit(self) -> None` | Commit the current transaction. Raises `CommitOutsideUnitOfWorkError` if called outside a `UnitOfWork` context. |
| `rollback` | `rollback(self) -> None` | Roll back the current transaction. |
| `close` | `close(self) -> None` | Release session resources. |
| `is_dirty` | `is_dirty(self) -> bool` | Check whether uncommitted changes exist. |

### Free Methods

Beyond the required methods, you can add any methods your database adapter needs. Each session subclass exposes the API that makes sense for its technology:

```python
class RedisSession(Session):
    def get(self, key: str) -> object: ...
    def set(self, key: str, value: object) -> None: ...
    def hmset(self, key: str, mapping: dict) -> None: ...
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def is_dirty(self) -> bool: ...
```

```python
class PostgresSession(Session):
    def execute(self, operation: object, params: dict | None = None) -> object: ...
    def query(self, statement: str) -> list[dict]: ...
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def is_dirty(self) -> bool: ...
```

You define the interface your database needs.

## AsyncSession

```python
from aod.infrastructure import AsyncSession
```

`AsyncSession(Port)` is an abstract base class for asynchronous database sessions.

### Required Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `begin` | `async begin(self) -> None` | Start a new transaction asynchronously. |
| `commit` | `async commit(self) -> None` | Commit the current transaction. Raises `CommitOutsideUnitOfWorkError` if called outside a `UnitOfWork` context. |
| `rollback` | `async rollback(self) -> None` | Roll back the current transaction asynchronously. |
| `close` | `async close(self) -> None` | Release session resources asynchronously. |
| `is_dirty` | `is_dirty(self) -> bool` | Check whether uncommitted changes exist. This method is **sync** even on `AsyncSession`. |

Same freedom applies — add async-specific methods as needed.

```python
class AsyncRedisSession(AsyncSession):
    async def get(self, key: str) -> object: ...
    async def set(self, key: str, value: object) -> None: ...
    async def begin(self) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def close(self) -> None: ...
    def is_dirty(self) -> bool: ...
```

## Transaction Pattern

A session must **never** call `commit()` or `rollback()` directly. The `UseCase` wrapper handles transactions automatically through an internal `UnitOfWork`:

1. The UseCase wrapper opens a `UnitOfWork` context before `run()` executes
2. If `run()` completes without error, the wrapper calls `commit()` on all dirty sessions
3. If `run()` raises, the wrapper calls `rollback()`

The `commit()` method is decorated to raise `CommitOutsideUnitOfWorkError` if called manually outside this context. This guarantees that transaction control stays in the framework — session implementations focus only on data operations, not transaction management.

```python
class PostgresSession(Session):
    def execute(self, operation: object) -> object:
        return self.connection.execute(operation)

    def begin(self) -> None:
        self.connection.begin()

    def commit(self) -> None:          # raises CommitOutsideUnitOfWorkError
        self.connection.commit()       # if called manually

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        self.connection.close()

    def is_dirty(self) -> bool:
        return self.connection.is_dirty()

## Testing with SpySession

```python
from aod.testing.doubles import SpySession, SpyAsyncSession
```

`SpySession` and `SpyAsyncSession` track calls and let you configure return values on every lifecycle method:

```python
spy = SpySession()

spy.is_dirty.returns(True)           # next call returns True
spy.is_dirty.always_returns(False)   # always returns False
spy.is_dirty.called                  # True if called
spy.is_dirty.call_count              # number of calls
spy.is_dirty.calls                   # list of call argument lists
spy.begin.called                     # tracks begin() too
```

For user-defined methods (e.g. `get`, `set`, `execute`), extend the spy or use your own test double.

## Next Steps

<div class="home-features">

</div>