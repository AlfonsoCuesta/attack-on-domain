# Quick Start

This guide walks through building a user registration system with `attack-on-domain` in 5 steps.

## 1. Define Value Objects, Events, and Root Entity

Value Objects are immutable, identity-less types. Events record what happened. Root Entities have identity and enforce invariants.

```python
from aod.domain import ValueObject, RootEntity
from aod.events import Event


class Email(ValueObject):
    value: str


class UserRegistered(Event):
    user_id: str
    email: str


class User(RootEntity):
    id: str
    email: Email
    name: str

    def register(self) -> None:
        self._event_emitter.emit(
            UserRegistered(user_id=self.id, email=self.email.value)
        )
```

## 2. Define a Command and its Handler

Commands are immutable requests to change state. Handlers contain the infrastructure logic to execute them.

```python
from aod.application import Command
from aod.infrastructure import CommandHandler


class RegisterUser(Command[User, None]):
    user_id: str
    email: str
    name: str


class RegisterUserHandler(CommandHandler[RegisterUser]):
    def handle(self, command: RegisterUser) -> None:
        user = User(
            id=command.user_id,
            email=Email(value=command.email),
            name=command.name,
        )
        self.session.execute(user)
```

## 3. Create a Use Case with CommandPort

Use Cases orchestrate domain logic. They depend on `CommandPort[Command]` and `QueryPort[Query]` — NOT custom repository ports. Values flow through `run()` parameters.

```python
from aod.application import UseCase, CommandPort


class RegisterUserUseCase(UseCase):
    save_user: CommandPort[RegisterUser]

    def run(self, user_id: str, email: str, name: str) -> None:
        user = User(
            id=user_id,
            email=Email(value=email),
            name=name,
        )
        user.register()
        self.save_user.handle(RegisterUser(
            user_id=user_id, email=email, name=name,
        ))
```

## 4. Wire It Together

Use `AdapterContainerBase` and `inject_adapters`. The container discovers handlers and auto-wires them into the use case.

```python
from aod.infrastructure import AdapterContainerBase, inject_adapters


class AppContainer(AdapterContainerBase):
    handlers: list = [RegisterUserHandler]


container = AppContainer()
use_case = inject_adapters(container, RegisterUserUseCase)

use_case.run(user_id="2", email="alice@example.com", name="Alice")
```

## 5. Test It

Use `build()` to construct objects without validation, `events_of()` to inspect emitted events, `assert_event_emitted()` for assertions, and `SpySession` for handler testing.

```python
from aod.testing import build, events_of, assert_event_emitted
from aod.testing.doubles import SpyLogger, SpySession


user = build(User, id="1", email=Email(value="test@example.com"), name="Test")

user.register()

assert len(events_of(user)) == 1
assert_event_emitted(user, UserRegistered)

# Test handler with SpySession
handler = RegisterUserHandler(session=SpySession())
handler.handle(RegisterUser(user_id="2", email="alice@example.com", name="Alice"))
assert handler.handle.called
```

## Next Steps

- [DDD Concepts](concepts.md) — Understand the theory behind the building blocks
- [Domain Objects](../domain/index.md) — Detailed API for entities, value objects, and services
- [Testing Utilities](../testing/index.md) — More testing patterns and assertions
- [Injection](../infrastructure/injection.md) — Dependency injection in depth