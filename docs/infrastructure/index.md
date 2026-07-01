# Infrastructure Layer

The infrastructure layer provides concrete implementations of ports and handles external concerns like databases, APIs, and file systems.

## Building Blocks

| Block | Description | Purpose |
|-------|-------------|---------|
| [Session](sessions.md) | Database abstraction | Handle connections and transactions |
| [Handler](handlers.md) | Command/Query processor | Implement `CommandPort` / `QueryPort` |
| [Projection](projections.md) | Read/write models | Query data efficiently |
| [Container](container.md) | Dependency injection | Wire ports, handlers, sessions into use cases and projections |

## Imports

```python
from aod.infrastructure import (
    Session,
    AsyncSession,
    ReadProjection,
    WriteProjection,
    Projection,
    AdapterContainer,
    CommandHandler,
    QueryHandler,
)
```

## Quick Example

```python
from aod.infrastructure import (
    Session,
    AdapterContainer,
    CommandHandler,
)

# Define a session
class PostgresSession(Session):
    def execute(self, operation: object) -> object: ...
    def query(self, operation: object) -> object: ...
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def is_dirty(self) -> bool: ...

class RedisSession(Session):
    def get(self, key: str) -> object: ...
    def set(self, key: str, value: object) -> None: ...
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def is_dirty(self) -> bool: ...

# Define a handler
class CreateUserHandler(CommandHandler[CreateUser]):
    session: PostgresSession

    def handle(self, command: CreateUser) -> None:
        self.session.execute(...)

# Define a container
container = AdapterContainer(sessions={PostgresSession}, handlers=[CreateUserHandler])
use_case = container.adapt_use_case(PlaceOrderUseCase)
```

## Key Concepts

### Sessions

Sessions abstract database operations. The base class defines five abstract lifecycle methods (`begin`, `commit`, `rollback`, `close`, `is_dirty`). Subclasses add the methods their database needs:

```python
from aod.infrastructure import Session

class PostgresSession(Session):
    def execute(self, operation: object) -> object:
        pass

    def query(self, operation: object) -> object:
        pass

    def begin(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return False
```

Each subclass defines its own data interface — `RedisSession` exposes `get`/`set`, `PostgresSession` exposes `execute`/`query`, etc.

### Projections

Projections read and write data. Declare a concrete session type and use `DTO` subclasses for input:

```python
from aod.application import DTO
from aod.infrastructure import ReadProjection
from aod.infrastructure import Session

# Define your session first
class PostgresSession(Session):
    def execute(self, operation: object) -> object: ...
    def query(self, operation: object) -> object: ...
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def is_dirty(self) -> bool: ...

class UserSearch(DTO):
    user_id: str

class UserListProjection(ReadProjection):
    session: PostgresSession

    def read(self, model: UserSearch) -> list[User]:
        return self.session.query("SELECT * FROM users")
```

### Containers

Containers wire ports to implementations:

```python
from aod.infrastructure import AdapterContainer

container = AdapterContainer(sessions={PostgresSession}, handlers=[CreateUserHandler, GetUserHandler])
```

### Injection

Wire dependencies into use cases via the container:

```python
container = AdapterContainer()
use_case = container.adapt_use_case(CreateUserUseCase)
```

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="sessions.md">Session</a></h3>
<p>Learn about database sessions</p>
</div>

<div class="feature-card">
<h3><a href="handlers.md">Handler</a></h3>
<p>Learn about command/query handlers</p>
</div>

<div class="feature-card">
<h3><a href="projections.md">Projection</a></h3>
<p>Learn about read/write projections</p>
</div>

<div class="feature-card">
<h3><a href="container.md">Container</a></h3>
<p>Learn about dependency injection</p>
</div>

</div>