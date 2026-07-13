# Application Layer

The application layer orchestrates domain objects through use cases. It defines interfaces (ports) for infrastructure and provides contracts for communication.

## Building Blocks

| Block | Description | Purpose |
|-------|-------------|---------|
| [UseCase](use-cases.md) | Application operation | Orchestrate domain logic |
| [Port](ports.md) | Interface definition | Abstract infrastructure |
| [Command](contracts.md) | Write operation | Request to change state |
| [Query](contracts.md) | Read operation | Request to read state |
| [Handler](../infrastructure/handlers.md) | Command/Query processor | Execute contracts |

## Imports

```python
from aod.application import (
    UseCase,
    AsyncUseCase,
    Port,
    Command,
    Query,
    CommandPort,
    QueryPort,
    Logger,
    EventBus,
)
from aod.application.cache import Cache, AsyncCache
```

## Quick Example — CQRS

```python
from aod.application import UseCase, Command, CommandPort

# Define a command (immutable write request)
class CreateUser(Command[User, None]):
    user_id: str
    name: str
    email: str

# Define a use case with a CommandPort
class CreateUserUseCase(UseCase):
    save_user: CommandPort[CreateUser]

    def run(self, user_id: str, name: str, email: str) -> None:
        user = User(id=user_id, name=name, email=email)
        self.save_user.handle(CreateUser(
            user_id=user_id, name=name, email=email,
        ))
        self._event_emitter.emit(UserCreated(user_id=user_id))

# The container injects the matching CommandHandler
uc = container.adapt(CreateUserUseCase)
uc.run(user_id="1", name="Alice", email="alice@example.com")
```

## Key Concepts

### Port Types

Use case fields must be `Port` subclasses. The framework provides two kinds:

| Kind | Purpose | Examples |
|------|---------|----------|
| **Handler ports** | Database operations | `CommandPort[T]`, `QueryPort[T]` |
| **Service ports** | External concerns | Custom `Port` subclasses |

### CommandPort / QueryPort for Database Operations

```python
# Correct: CommandPort as field, values in run()
class CreateUserUseCase(UseCase):
    save_user: CommandPort[CreateUser]

    def run(self, user_id: int, name: str) -> None:
        user = User(id=user_id, name=name)
        self.save_user.handle(CreateUser(user_id=user_id, name=name))

# Wrong: values as fields
class CreateUserUseCase(UseCase):
    user_id: int  # InvalidUseCasePortFieldError!
    name: str     # InvalidUseCasePortFieldError!
```

### Custom Service Port for External Concerns

For non-database dependencies (API clients, notification services, etc.), create custom `Port` subclasses:

```python
from aod.application import Port, UseCase


class NotificationClient(Port):
    def send_email(self, to: str, subject: str, body: str) -> None: ...


class NotifyUser(UseCase):
    notification: NotificationClient

    def run(self, user_id: str, message: str) -> None:
        user = User(id=user_id)
        self.notification.send_email(to=user.email, subject="Alert", body=message)
```

### Blocked Field Types

`Session` and `AsyncSession` are rejected on UseCases:

```python
from aod.infrastructure import Session

class CreateUserUseCase(UseCase):
    session: Session  # InvalidUseCasePortFieldError!

    def run(self) -> None:
        pass
```

Instead, use `CommandPort[Command]` or `QueryPort[Query]`:

```python
from aod.application import CommandPort, Command

class CreateUser(Command[User, None]):
    user_id: str
    name: str
    email: str

class CreateUserUseCase(UseCase):
    save_user: CommandPort[CreateUser]

    def run(self) -> None:
        pass
```

### Auto-Wired Fields

Use cases have one private auto-wired field:

```python
class CreateUser(UseCase):
    # _uow is private and auto-created, no need to declare
    # It manages transactions, committing on success and rolling back on failure
    # Cache flushing happens inside _uow.commit() — not visible to the UseCase

    def run(self) -> None:
        pass
```

`Logger` and `EventBus` are not auto-wired. Declare them as normal ports when you need them:

```python
class CreateUser(UseCase):
    logger: Logger
    event_bus: EventBus

    def run(self, user_id: str, name: str) -> None:
        ...
```

### Cache

Cache is injected via handlers, not the UseCase. Use `handler.add_cache(cache)` when building your handler, and the container wires it automatically. Import from `aod.application.cache`:

```python
from aod.application.cache import Cache, AsyncCache

class MyCache(Cache):
    def get(self, key: str) -> object | None: ...
    def set(self, key: str, value: object, ttl: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...
```

### Event Collection

Events emitted during `run()` are automatically collected:

```python
class CreateUserUseCase(UseCase):
    save_user: CommandPort[CreateUser]

    def run(self, user_id: str, name: str) -> None:
        user = User(id=user_id, name=name)
        self.save_user.handle(CreateUser(user_id=user_id, name=name, email=""))
        self._event_emitter.emit(UserCreated(user_id=user_id))

uc = CreateUserUseCase(save_user=handler)
uc.run(user_id="1", name="Alice")
assert len(uc.events) == 1
```

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="use-cases.md">UseCase</a></h3>
<p>Detailed UseCase API</p>
</div>

<div class="feature-card">
<h3><a href="ports.md">Port</a></h3>
<p>Learn about ports</p>
</div>

<div class="feature-card">
<h3><a href="contracts.md">Contracts</a></h3>
<p>Learn about commands and queries</p>
</div>

<div class="feature-card">
<h3><a href="../infrastructure/handlers.md">Handlers</a></h3>
<p>Learn about command/query handlers</p>
</div>

</div>
