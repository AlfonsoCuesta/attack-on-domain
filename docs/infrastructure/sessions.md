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
| `commit` | `commit(self) -> None` | Commit the current transaction. Raises `CommitOutsideUnitOfWorkError` if called outside a `Transaction` context. |
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
| `commit` | `async commit(self) -> None` | Commit the current transaction. Raises `CommitOutsideUnitOfWorkError` if called outside a `Transaction` context. |
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

A session must **never** call `begin()`, `commit()`, or `rollback()` directly. The UseCase creates a `Transaction` internally (not injected by the container) and wraps `run()` with automatic transaction management.

### The Transaction Flow (Internal to UseCase)

```python
# This is what happens inside use_case.run():
tx.begin()                              # calls session.begin() on ALL sessions
    # Your run() code executes here
    # CommandHandlers write via session.execute()
    # QueryHandlers read via session.query()
if run() succeeds:
    tx.commit()                         # calls session.commit() ONLY on dirty sessions
    # caches flushed (via CacheContext.flush())
    for bus in _event_buses:
        bus.publish(*events)            # publishes collected events
if run() fails:
    tx.rollback()                       # calls session.rollback() ONLY on dirty sessions
    # caches discarded (via CacheContext.discard())
    error re-raised                     # exception propagates to caller
```

Key points:
- The Transaction is created internally by the UseCase -- you never construct or inject one.
- Caches are managed via `CacheContext` (activated by `CacheManager`). The container wraps operations with `CacheManager` automatically. Flush happens after commit, discard happens on rollback.
- Only dirty sessions are committed/rolled back (checked via `is_dirty()`)
- `commit()` is guarded by `_CommitContext` ContextVar -- raises `CommitOutsideUnitOfWorkError` if called outside a Transaction
- `begin()` and `rollback()` are NOT guarded -- they can be called anywhere (though you should never need to)
- QueryHandlers don't participate in transactions -- they read data without begin/commit/rollback

### Commit Guard

The `commit()` method on every Session subclass is auto-wrapped at class creation time with a check against a `_CommitContext` flag. This flag is set to `True` only inside a Transaction `commit()`. Any direct call to `session.commit()` outside a Transaction immediately raises `CommitOutsideUnitOfWorkError`:

```python
postgres = PostgresSession()
postgres.commit()  # CommitOutsideUnitOfWorkError!

# Inside a UseCase it works fine:
use_case = container.adapt(PlaceOrderUseCase)
use_case.run(...)  # tx.commit() sets the flag -> session.commit() succeeds
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

## Testing with Spy Sessions

```python
from aod.testing.doubles import spy_session
```

`spy_session` generates a stub class from any `Session` or `AsyncSession` subclass. Every method — including custom methods your concrete session defines — becomes a `MagicMock` (or `AsyncMock` for async sessions). `is_dirty()` returns `False` by default.

```python
StubPg = spy_session(PgSession)
session = StubPg()

session.is_dirty.return_value = True
session.query.return_value = [{"id": 1}]
session.set.return_value = True  # custom method is also mocked
assert session.begin.called
assert session.commit.called
```

## Next Steps

<div class="home-features">

</div>
