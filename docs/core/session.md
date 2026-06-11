# Session

`Session` is an abstract base class for database sessions. It lives in the infrastructure layer (`from aod.infrastructure import Session`) and extends `Port`. An `AsyncSession` variant with coroutine methods is also available.

## Sync `Session`

```python
class Session(Port):
    @abstractmethod
    def execute(self, operation: object) -> object: ...
    @abstractmethod
    def query(self, operation: object) -> object: ...
    @abstractmethod
    def begin(self) -> None: ...
    @abstractmethod
    def commit(self) -> None: ...
    @abstractmethod
    def rollback(self) -> None: ...
    @abstractmethod
    def close(self) -> None: ...
    @abstractmethod
    def is_dirty(self) -> bool: ...
```

## Async `AsyncSession`

```python
class AsyncSession(Port):
    @abstractmethod
    async def execute(self, operation: object) -> object: ...
    @abstractmethod
    async def query(self, operation: object) -> object: ...
    @abstractmethod
    async def begin(self) -> None: ...
    @abstractmethod
    async def commit(self) -> None: ...
    @abstractmethod
    async def rollback(self) -> None: ...
    @abstractmethod
    async def close(self) -> None: ...
    @abstractmethod
    def is_dirty(self) -> bool: ...
```

### Common Operations

## PostgreSQL Example

```python
from __future__ import annotations

from typing import Any

import asyncpg
from aod.infrastructure import Session


class PostgresSession(Session):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._conn: asyncpg.Connection | None = None
        self._log: list[tuple[str, list[Any]]] = []
        self._committed = False

    async def execute(self, operation: object) -> object:
        sql, *params = _unpack(operation)  # user-defined (sql, params)
        conn = self._conn or await self._pool.acquire()
        result = await conn.execute(sql, *params)
        self._log.append((sql, params))
        return result

    async def query(self, operation: object) -> object:
        sql, *params = _unpack(operation)
        conn = self._conn or self._pool
        return await conn.fetch(sql, *params)

    async def begin(self) -> None:
        self._conn = await self._pool.acquire()
        await self._conn.execute("BEGIN")

    async def commit(self) -> None:
        if self._conn:
            await self._conn.execute("COMMIT")
            self._committed = True

    async def rollback(self) -> None:
        if not self._committed and self._conn:
            # Real ROLLBACK — no commit happened yet
            await self._conn.execute("ROLLBACK")
        elif self._committed and self._log:
            # Compensation — commit already happened,
            # run inverse operations in reverse order
            for sql, params in reversed(self._log):
                await self._pool.execute(_inverse(sql, params))
        self._log.clear()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
```

Helper functions `_unpack` and `_inverse` are application‑specific (convert domain operations to SQL and compute inverse statements).

## MongoDB Example

```python
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from aod.infrastructure import Session


class MongoSession(Session):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._log: list[dict[str, Any]] = []
        self._committed = False

    async def execute(self, operation: object) -> object:
        op = _to_dict(operation)  # user-defined: → {"collection", "action", "filter", "data"}
        collection = self._db[op["collection"]]

        if op["action"] == "insert":
            result = await collection.insert_one(op["data"])
        elif op["action"] == "update":
            result = await collection.update_one(op["filter"], op["data"])
        elif op["action"] == "delete":
            result = await collection.delete_one(op["filter"])
        else:
            raise ValueError(f"Unknown action: {op['action']}")

        self._log.append(op)
        return result

    async def query(self, operation: object) -> object:
        op = _to_dict(operation)
        collection = self._db[op["collection"]]
        return await collection.find(op.get("filter", {})).to_list(None)

    async def begin(self) -> None:
        self._log.clear()

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        if not self._committed:
            # Nothing to rollback — no transaction in Mongo
            pass
        elif self._log:
            # SAGA compensation in reverse order
            for op in reversed(self._log):
                collection = self._db[op["collection"]]
                if op["action"] == "insert":
                    await collection.delete_one({"_id": op.get("inserted_id")})
                elif op["action"] == "update":
                    await collection.update_one(op["filter"], op["rollback_data"])
                elif op["action"] == "delete":
                    await collection.insert_one(op["deleted_doc"])
        self._log.clear()

    async def close(self) -> None:
        self._db.client.close()
```

## Integration with UnitOfWork

A `UnitOfWork` receives a single `Session` (or multiple via `repositories`) and delegates `commit`/`rollback` to it. The session decides whether `rollback()` means a real ROLLBACK or a compensation chain:

```python
uow = MyUnitOfWork(session=PostgresSession(pool))
async with uow:
    result = await uow.command(CreateUser(name="Alice"))
# On success → commit()
# On exception → rollback()
```
