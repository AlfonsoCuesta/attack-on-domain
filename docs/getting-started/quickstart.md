# Quick Start

This guide walks through building a user registration system with `attack-on-domain` in 5 steps.

## 1. Define Value Objects and Events

Value Objects are immutable, identity-less types. Events record what happened in the domain.

```python
from aod.domain import ValueObject
from aod.events import Event


class Email(ValueObject):
    value: str


class Money(ValueObject):
    amount: float
    currency: str


class UserRegistered(Event):
    user_id: str
    email: str
```

## 2. Define a Root Entity

Root Entities are mutable objects with identity. Public methods can mutate fields and emit events via `_event_emitter`.

```python
from aod.domain import RootEntity


class User(RootEntity):
    id: str
    email: Email
    name: str

    def register(self) -> None:
        self._event_emitter.emit(
            UserRegistered(user_id=self.id, email=self.email.value)
        )
```

## 3. Define a Port

Ports are abstract interfaces the application layer depends on. Infrastructure provides concrete implementations.

```python
from aod.application import Port


class UserClient(Port):
    def save(self, user: User) -> None: ...
    def find(self, user_id: str) -> User | None: ...
```

## 4. Create a Use Case

Use Cases orchestrate domain objects. Fields must be Port subclasses. Values flow through `run()` parameters.

```python
from aod.application import UseCase


class RegisterUser(UseCase):
    user_client: UserClient

    def run(self, user_id: str, email: str, name: str) -> None:
        user = User(
            id=user_id,
            email=Email(value=email),
            name=name,
        )
        user.register()
        self.user_client.save(user)
```

## 5. Test It

Use `build()` to construct objects without validation, `events_of()` to inspect emitted events, and `assert_event_emitted()` for assertions.

```python
from aod.testing import build, events_of, assert_event_emitted
from aod.testing.doubles import SpyLogger


user = build(User, id="1", email=Email(value="test@example.com"), name="Test")

user.register()

assert len(events_of(user)) == 1
assert_event_emitted(user, UserRegistered)

container = AppContainer(user_client=user_client_instance)
use_case = inject_adapters(container, RegisterUser)

use_case.run(user_id="2", email="alice@example.com", name="Alice")
```

To wire ports to implementations, use `AdapterContainerBase` and `inject_adapters`:

```python
from aod.infrastructure import AdapterContainerBase, inject_adapters


class RealUserClient(UserClient):
    def save(self, user: User) -> None:
        print(f"Saving user {user.id}")

    def find(self, user_id: str) -> User | None:
        return None


class AppContainer(AdapterContainerBase):
    user_client: UserClient


container = AppContainer(user_client=RealUserClient())
use_case = inject_adapters(container, RegisterUser)

use_case.run(user_id="2", email="alice@example.com", name="Alice")
```

## Next Steps

- [DDD Concepts](concepts.md) — Understand the theory behind the building blocks
- [Domain Objects](../domain/index.md) — Detailed API for entities, value objects, and services
- [Testing Utilities](../testing/index.md) — More testing patterns and assertions
- [Injection](../infrastructure/injection.md) — Dependency injection in depth