# Cache

`Cache` is an abstract port for key-value caching. Extends `Port`, available at `from aod.application import Cache` (sync) or `from aod.application.cache.async_ import Cache` (async).

```python
class Cache(Port):
    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any, ttl: float | None = None) -> None: ...
    def delete(self, key: str) -> None: ...
```

- **`get(key)`** — retrieve by key, returns `None` if missing
- **`set(key, value, ttl=None)`** — store with optional TTL in seconds
- **`delete(key)`** — remove key

## Redis Example

```python
import json
from typing import Any

from redis.asyncio import Redis
from aod.application.cache.async_ import Cache


class RedisCache(Cache):
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get(self, key: str) -> Any:
        value = await self._client.get(key)
        return json.loads(value) if value is not None else None

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        await self._client.set(key, json.dumps(value), ex=ttl)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)
```

## Usage in a UseCase

`Cache` is a Port like any other — inject it into a `UseCase` or `Handler`:

```python
class GetUserUseCase(UseCase):
    cache: Cache
    handler: QueryHandler[GetUserQuery, User]

    async def run(self) -> User:
        user = await self.cache.get(self.command.user_id)
        if user is not None:
            return user
        user = await self.handler.handle(self.command)
        await self.cache.set(self.command.user_id, user, ttl=300)
        return user
```

## Composition over Injection

Cache is infrastructure, not domain. To keep handlers clean, compose cache inside a concrete `Session` or `Repository`:

```python
class CachedUserRepository(Session):
    def __init__(self, db: Session, cache: Cache) -> None:
        self._db = db
        self._cache = cache

    async def query(self, operation: object) -> object:
        key = self._cache_key(operation)
        if (result := await self._cache.get(key)) is not None:
            return result
        result = await self._db.query(operation)
        await self._cache.set(key, result)
        return result
```

The handler stays decoupled — it only sees a `Session`.
