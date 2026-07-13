# attack-on-domain

**Domain-Driven Design building blocks for Python 3.14+** — entities, value objects, aggregates, CQRS, ports and adapters, use cases, domain events, invariants, and dependency injection. All running on Pydantic v2, fully typed, with mutation guards that actually work.

No ORM. No framework lock-in. No "just pip install django and pray."

---

## Why This Exists

You have a complex domain. Your codebase is turning into a big ball of mud. Your entities are anemic, your services are god objects, and somehow `User` extends `AbstractBaseModelMixinFactory` in six different ways.

**attack-on-domain** gives you real DDD primitives:

- **Entities** with enforced identity fields (one, exactly one, or the class doesn't compile)
- **Value Objects** that are actually immutable — no `@property` hacks, no `__setattr__` tricks
- **Root Entities** that know they're the aggregate root and refuse to be nested inside anything else
- **Mutation guards** that block writes from outside your methods (`user.name = "hacker"` raises `MutationForbiddenException` — try that with a dataclass)
- **Business invariants** via decorators that turn `ValueError` into `InvarianceException` at construction time
- **CQRS** that's built-in, not bolted on — `Command[TEntity, TResult]` and `Query[TEntity, TResult]` with compile-time generic validation
- **Event collection** that Just Works — emit from entities, VOs, services; UseCases collect them automatically; `EventCollector` context manager catches cross-aggregate events
- **Ports & adapters** — `CommandPort[T]` / `QueryPort[T]` on UseCases, infrastructure handlers implement them, `AdapterContainer` wires everything. No service locator, no global state, no singletons.

## AI-Native by Design

LLMs are great at generating code. They're terrible at maintaining implicit invariants. This framework makes invariants **explicit**:

- Every entity identity is declared up front — the LLM can't "forget" which field is the ID
- Every mutation boundary is enforced at runtime — the LLM can't accidentally write `self.total = 0` outside a method
- Every event emission is tracked — the LLM can't emit events that go nowhere
- Every port is an interface — the LLM generates adapters against a contract, not implementation details

The result: **an AI agent can safely generate, refactor, and extend your domain code without silently breaking business rules.** Try that with a plain Pydantic model.

### Built-in Agent Skill

This repo ships with a skill at `skills/attack-on-domain/` — a comprehensive reference that teaches agents how to use the library correctly. Load it with `/load attack-on-domain` or install it with skills library:

```bash
npx skills add alfonsocuesta/attack-on-domain
```

It will ask questions you haven't thought of. It's annoying on purpose. Your domain will be better for it.

## Quick Example

```python
from aod.domain import RootEntity, ValueObject, Field
from aod.events import Event
from aod.application import UseCase, Command, CommandPort
from aod.infrastructure import CommandHandler, Session, AdapterContainer


class SqlSession(Session):
    def execute(self, operation: object) -> None: ...
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def is_dirty(self) -> bool:
        return False


class OrderId(ValueObject):
    value: str


class OrderPlaced(Event):
    order_id: str
    total: float


class Order(RootEntity):
    id: OrderId = Field(id=True)
    total: float

    def place(self) -> None:
        self._event_emitter.emit(
            OrderPlaced(order_id=self.id.value, total=self.total)
        )


class PlaceOrder(Command[Order, None]):
    order_id: str
    total: float


class PlaceOrderHandler(CommandHandler[PlaceOrder]):
    session: SqlSession

    def handle(self, command: PlaceOrder) -> None:
        self.session.execute(command)


class PlaceOrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]

    def run(self, order_id: str, total: float) -> None:
        order = Order(id=OrderId(value=order_id), total=total)
        order.place()
        self.place_order.handle(PlaceOrder(order_id=order_id, total=total))


container = AdapterContainer(
    sessions={SqlSession},
    handlers=[PlaceOrderHandler],
)
use_case = container.adapt(PlaceOrderUseCase)
use_case.run(order_id="1", total=99.99)
# Events are auto-collected: use_case.events -> [OrderPlaced(...)]
```

## FastAPI? You Bet.

Because the framework keeps infrastructure out of your domain, wiring it into FastAPI is a few lines:

```python
from functools import lru_cache
from fastapi import FastAPI, Depends
from aod.application import UseCase
from aod.application.async_ import UseCase as AsyncUseCase
from aod.infrastructure import AdapterContainer

from yourdomain import CreateUserUseCase, CreateUserInput
from yourinfra import PostgresSession, CreateUserHandler

app = FastAPI()

@lru_cache
def get_container() -> AdapterContainer:
    return AdapterContainer(
        sessions={PostgresSession},
        handlers=[CreateUserHandler],
    )

def get_use_case(
    use_case: type[UseCase | AsyncUseCase],
    container: AdapterContainer = Depends(get_container),
):
    return container.adapt(use_case)

@app.post("/users")
def create_user(
    payload: CreateUserInput,
    use_case: CreateUserUseCase = Depends(get_use_case(CreateUserUseCase)),
):
    return use_case.run(payload)
```

The same use case works with CLI scripts, background workers, and tests. No `@app` decorators in your domain. No `async def` leaks into entities. Just ports, adapters, and a container.

## Install

```bash
uv add attack-on-domain
```

Or with pip:

```bash
pip install attack-on-domain
```

Requires **Python 3.14+**.

## Documentation

Full docs at [alfonsocuesta.github.io/attack-on-domain](https://alfonsocuesta.github.io/attack-on-domain/)

| You Want To | Go Here |
|-------------|---------|
| Install & first 5 minutes | [Getting Started](docs/getting-started/installation.md) |
| Learn the building blocks | [Domain Layer](docs/domain/index.md) |
| Orchestrate with use cases | [Application Layer](docs/application/index.md) |
| Write database adapters | [Infrastructure Layer](docs/infrastructure/index.md) |
| Test without mocks | [Testing](docs/testing/index.md) |
| Map DDD concepts to code | [DDD to AoD](docs/getting-started/mapping.md) |
| Full API reference | [API Reference](docs/api/index.md) |

## License

Apache 2.0
