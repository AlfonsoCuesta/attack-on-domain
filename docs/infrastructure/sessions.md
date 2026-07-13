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

Same freedom applies -- add async-specific methods as needed.

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

A session must **never** call `begin()`, `commit()`, or `rollback()` directly. The UseCase creates a `UnitOfWork` internally (not injected by the container) and wraps `run()` with automatic transaction management.

### The UnitOfWork Flow (Internal to UseCase)

```python
# This is what happens inside use_case.run():
uow.begin()                             # calls session.begin() on ALL sessions
    # Your run() code executes here
    # CommandHandlers write via session.execute()
    # QueryHandlers read via session.query()
if run() succeeds:
    uow.commit()                        # calls session.commit() ONLY on dirty sessions
    for cache in self.caches:
        cache._flush()                  # flushes caches wired to handlers via add_cache()
    for bus in _event_buses:
        bus.publish(*events)            # publishes collected events
if run() fails:
    uow.rollback()                      # calls session.rollback() ONLY on dirty sessions
    error re-raised                     # exception propagates to caller
```

Key points:
- The UnitOfWork is created internally by the UseCase -- you never construct or inject one.
- Caches flushed during `uow.commit()` come from handlers that registered them via `add_cache()`. The container auto-wires caches to matching handlers when the handler is instantiated.
- Only dirty sessions are committed/rolled back (checked via `is_dirty()`)
- `commit()` is guarded by `_CommitContext` ContextVar -- raises `CommitOutsideUnitOfWorkError` if called outside a UseCase
- `begin()` and `rollback()` are NOT guarded -- they can be called anywhere (though you should never need to)
- QueryHandlers don't participate in transactions -- they read data without begin/commit/rollback

### Commit Guard

The `commit()` method on every Session subclass is auto-wrapped at class creation time with a check against a `_CommitContext` flag. This flag is set to `True` only inside `uow.commit()`. Any direct call to `session.commit()` outside a UseCase immediately raises `CommitOutsideUnitOfWorkError`:

```python
postgres = PostgresSession()
postgres.commit()  # CommitOutsideUnitOfWorkError!

# Inside a UseCase it works fine:
use_case = container.adapt(PlaceOrderUseCase)
use_case.run(...)  # uow.commit() sets the flag -> session.commit() succeeds
```

This guarantees that transaction control stays in the framework -- session implementations focus only on data operations, not transaction management.

### Complete Example

```python
class PostgresSession(Session):
    _conn: object = PrivateField(default=None)

    def execute(self, sql: str, params: dict | None = None) -> None:
        self._conn.execute(sql, (params or {}))

    def query(self, sql: str, params: dict | None = None) -> list[dict]:
        cur = self._conn.cursor()
        cur.execute(sql, (params or {}))
        return [dict(row) for row in cur.fetchall()]

    def begin(self) -> None:
        self._conn.execute("BEGIN")

    def commit(self) -> None:          # auto-guarded -- raises if outside UseCase
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def is_dirty(self) -> bool:
        return self._conn.status == "dirty"
```

## Testing with SpySession

```python
from aod.testing.doubles import SpySession, SpyAsyncSession
```

`SpySession` and `SpyAsyncSession` track calls and let you configure return values on every lifecycle method:

```python
spy = SpySession()

spy.is_dirty.return_value = True      # always returns True
spy.is_dirty.side_effect = [True, False]  # first True, then False
spy.is_dirty.called                  # True if called
spy.is_dirty.call_count              # number of calls
spy.is_dirty.call_args_list          # list of call objects, each with .args and .kwargs
spy.begin.called                     # tracks begin() too
```

For user-defined methods (e.g. `get`, `set`, `execute`), extend the spy or use your own test double.

## Next Steps

<div class="home-features">

</div>
