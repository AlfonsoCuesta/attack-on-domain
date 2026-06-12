# Application Layer

The application layer orchestrates domain objects through use cases. It defines interfaces (ports) for infrastructure and provides contracts for communication.

## Building Blocks

| Block | Description | Purpose |
|-------|-------------|---------|
| [UseCase](use-cases.md) | Application operation | Orchestrate domain logic |
| [Port](ports.md) | Interface definition | Abstract infrastructure |
| [Command](contracts.md) | Write operation | Request to change state |
| [Query](contracts.md) | Read operation | Request to read state |
| [Handler](handlers.md) | Command/Query processor | Execute contracts |

## Imports

```python
from aod.application import (
    UseCase,
    AsyncUseCase,
    Port,
    Command,
    Query,
    Logger,
    EventBus,
    UnitOfWork,
    Cache,
)
```

## Quick Example

```python
from aod.application import UseCase, Port

# Define a port (interface)
class UserClient(Port):
    def save(self, user: User) -> None: ...
    def find(self, user_id: str) -> User | None: ...

# Define a use case
class CreateUser(UseCase):
    user_client: UserClient

    def run(self, user_id: str, name: str, email: str) -> None:
        user = User(id=user_id, name=name, email=email)
        self.user_client.save(user)
        self._event_emitter.emit(UserCreated(user_id=user_id))

# Use the use case
uc = CreateUser(user_client=RealUserClient())
uc.run(user_id="1", name="Alice", email="alice@example.com")
```

## Key Concepts

### Ports as Dependencies

Use case fields must be `Port` subclasses. Values are passed as parameters to `run()`:

```python
# Correct: Ports as fields, values in run()
class CreateUser(UseCase):
    user_client: UserClient  # Port dependency

    def run(self, user_id: int, name: str) -> None:
        user = User(id=user_id, name=name)
        self.user_client.save(user)

# Wrong: values as fields
class CreateUser(UseCase):
    user_id: int  # InvalidUseCasePortFieldError!
    name: str     # InvalidUseCasePortFieldError!
```

### Blocked Field Types

`Session` and `AsyncSession` are rejected on UseCases:

```python
from aod.infrastructure import Session

class CreateUser(UseCase):
    session: Session  # InvalidUseCasePortFieldError!

    def run(self) -> None:
        pass
```

Instead, use a repository port:

```python
class UserRepository(Port):
    def save(self, user: User) -> None: ...

class CreateUser(UseCase):
    user_repo: UserRepository  # OK — it's a Port

    def run(self) -> None:
        pass
```

### Auto-Wired Fields

Use cases have auto-wired fields with Null Object defaults:

```python
class CreateUser(UseCase):
    # These are auto-wired, no need to declare
    # uow: UnitOfWork      — auto-commits on success
    # logger: Logger        — auto-logs completion
    # event_bus: EventBus   — auto-publishes events
    # cache: Cache          — auto-flushes after commit

    def run(self) -> None:
        pass
```

### Event Collection

Events emitted during `run()` are automatically collected:

```python
class CreateUser(UseCase):
    user_client: UserClient

    def run(self, user_id: str, name: str) -> None:
        user = User(id=user_id, name=name)
        self.user_client.save(user)
        self._event_emitter.emit(UserCreated(user_id=user_id))

uc = CreateUser(user_client=client)
uc.run(user_id="1", name="Alice")
assert len(uc.events) == 1
```

## Next Steps

- [UseCase](use-cases.md) — Detailed UseCase API
- [Port](ports.md) — Learn about ports
- [Contracts](contracts.md) — Learn about commands and queries
- [Handlers](handlers.md) — Learn about command/query handlers
