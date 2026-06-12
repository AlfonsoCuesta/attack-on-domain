# Infrastructure Layer

The infrastructure layer provides concrete implementations of ports and handles external concerns like databases, APIs, and file systems.

## Building Blocks

| Block | Description | Purpose |
|-------|-------------|---------|
| [Session](sessions.md) | Database abstraction | Handle connections and transactions |
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

# Define a handler
class CreateUserHandler(CommandHandler[CreateUser]):
    session: PostgresSession

    def handle(self, command: CreateUser) -> None:
        self.session.execute(...)

# Define a container
class AppContainer(AdapterContainerBase):
    sessions: set = {PostgresSession}
    handlers: list = [CreateUserHandler]

# Inject dependencies
container = AppContainer()
use_case = inject_adapters(container, PlaceOrderUseCase)
```

## Key Concepts

### Sessions

Sessions abstract database operations:

```python
from aod.infrastructure import Session

class PostgresSession(Session):
    def execute(self, operation: object) -> object:
        # Execute a write operation
        pass

    def query(self, operation: object) -> object:
        # Execute a read operation
        pass

    def begin(self) -> None:
        # Begin a transaction
        pass

    def commit(self) -> None:
        # Commit the transaction
        pass

    def rollback(self) -> None:
        # Rollback the transaction
        pass

    def close(self) -> None:
        # Close the connection
        pass

    def is_dirty(self) -> bool:
        # Check if there are uncommitted changes
        return False
```

### Projections

Projections read and write data:

```python
from aod.infrastructure import ReadProjection, ReadModel

class UserListProjection(ReadProjection):
    def read(self, model: ReadModel) -> list[User]:
        return self.session.query("SELECT * FROM users")
```

### Containers

Containers wire ports to implementations:

```python
from aod.infrastructure import AdapterContainerBase

class AppContainer(AdapterContainerBase):
    sessions: set = {PostgresSession}
    handlers: list = [CreateUserHandler, GetUserHandler]
```

### Injection

Inject dependencies into use cases:

```python
from aod.infrastructure import inject_adapters

container = AppContainer()
use_case = inject_adapters(container, CreateUserUseCase)
```

## Next Steps

- [Session](sessions.md) — Learn about database sessions
- [Projection](projections.md) — Learn about read/write projections
- [Container](container.md) — Learn about dependency injection
- [Injection](injection.md) — Learn about dependency injection
