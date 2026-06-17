# Infrastructure Layer

The infrastructure layer provides concrete implementations of ports and handles external concerns like databases, APIs, and file systems.

## Building Blocks

| Block | Description | Purpose |
|-------|-------------|---------|
| [Session](sessions.md) | Database abstraction | Handle connections and transactions |
| [Handler](handlers.md) | Command/Query processor | Implement `CommandPort` / `QueryPort` |
| [Projection](projections.md) | Read/write models | Query data efficiently |
| [Container](container.md) | Dependency injection | Wire ports to implementations |
| [Injection](injection.md) | Dependency injection | Inject dependencies into use cases |

## Imports

```python
from aod.infrastructure import (
    Session,
    AsyncSession,
    ReadProjection,
    WriteProjection,
    Projection,
    ReadModel,
    WriteModel,
    AdapterContainerBase,
    inject_adapters,
    CommandHandler,
    QueryHandler,
)
```

## Quick Example

```python
from aod.infrastructure import (
    Session,
    AdapterContainerBase,
    inject_adapters,
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
class AppContainer(AdapterContainerBase):
    pass

container = AppContainer(sessions={PostgresSession}, handlers=[CreateUserHandler])
use_case = inject_adapters(container, PlaceOrderUseCase)
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

Projections read and write data. Declare a concrete session type:

```python
from aod.infrastructure import ReadProjection, ReadModel
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


class UserListProjection(ReadProjection):
    session: PostgresSession

    def read(self, model: ReadModel) -> list[User]:
        return self.session.query("SELECT * FROM users")
```

### Containers

Containers wire ports to implementations:

```python
from aod.infrastructure import AdapterContainerBase

class AppContainer(AdapterContainerBase):
    pass


container = AppContainer(sessions={PostgresSession}, handlers=[CreateUserHandler, GetUserHandler])
```

### Injection

Inject dependencies into use cases:

```python
from aod.infrastructure import inject_adapters

container = AppContainer()
use_case = inject_adapters(container, CreateUserUseCase)
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

<div class="feature-card">
<h3><a href="injection.md">Injection</a></h3>
<p>Learn about dependency injection</p>
</div>

</div>