# Domain-Driven Design Concepts

This page explains the core DDD concepts implemented in `attack-on-domain`.

## What Is DDD?

Domain-Driven Design (DDD) is an approach to software development that focuses on:

1. **Putting the business domain first** — the code reflects how the business works
2. **Using a shared language** — developers and domain experts speak the same language (Ubiquitous Language)
3. **Creating clear boundaries** — different parts of the system map to distinct business subdomains

## The Building Blocks

### Value Objects

Immutable objects defined by their attributes, not their identity.

- No identity field
- Compared by value (all fields must match)
- Cannot be mutated after creation

```python
from aod.domain import ValueObject


class Money(ValueObject):
    amount: float
    currency: str


m1 = Money(amount=10.0, currency="USD")
m2 = Money(amount=10.0, currency="USD")
assert m1 == m2
```

### Entities

Mutable objects with a distinct identity that persists over time.

- Have an identity field (typically `id`)
- Can change state through public methods
- Compared by identity, not by value

```python
from aod.domain import Entity


class User(Entity):
    id: str
    name: str


u1 = User(id="1", name="Alice")
u2 = User(id="1", name="Bob")
assert u1 == u2  # Same identity
```

### Root Entities (Aggregates)

Entities that serve as the consistency boundary for a cluster of associated objects.

- Subclass `RootEntity` (not plain `Entity`)
- Cannot be nested inside other entities
- Enforce invariants across the aggregate

```python
from aod.domain import RootEntity


class Order(RootEntity):
    id: str
    total: float

    def apply_discount(self, percent: float) -> None:
        self.total *= 1 - percent
```

### Services

Stateless operations that do not naturally belong to any entity or value object.

- No identity or state
- Can depend on other services and entities
- Can emit domain events

```python
from aod.domain import Service


class TaxCalculator(Service):
    def calculate(self, amount: float, rate: float) -> float:
        return amount * rate
```

### Domain Events

Records of something significant that happened in the domain.

- Immutable and auto-timestamped (`emitted_at`)
- Emitted by entities and services via `_event_emitter`
- Automatically collected by use cases

```python
from aod.events import Event


class OrderPlaced(Event):
    order_id: str
    total: float
```

## Application Layer

### Use Cases

Application operations that orchestrate domain objects.

- Depend on Ports (interfaces), not concrete implementations
- Receive values as parameters to `run()`
- Auto-collect events, log, and publish to event bus

```python
from aod.application import UseCase


class PlaceOrder(UseCase):
    order_client: OrderClient

    def run(self, order_id: str, total: float) -> None:
        order = Order(id=order_id, total=total)
        self.order_client.save(order)
```

### Ports

Interfaces that define how the application interacts with the outside world. Infrastructure provides concrete implementations.

- Abstract base classes with method stubs
- Mutable from inside public methods
- Implementation is injected at runtime

```python
from aod.application import Port


class OrderClient(Port):
    def save(self, order: Order) -> None: ...
    def find(self, order_id: str) -> Order | None: ...
```

### Contracts

Immutable data classes for commands (writes) and queries (reads).

- `Command[TEntity, TResult]` — write operations
- `Query[TEntity, TResult]` — read operations
- Type-checked to ensure only `RootEntity` types are referenced

```python
from aod.application import Command, Query


class PlaceOrder(Command[Order, None]):
    order_id: str
    total: float


class GetOrder(Query[Order, Order | None]):
    order_id: str
```

## Infrastructure Layer

### Sessions

Database abstractions that handle connections and transactions.

- `Session` for synchronous databases
- `AsyncSession` for asynchronous databases
- Provide `begin()`, `commit()`, `rollback()`, `close()` lifecycle

```python
from aod.infrastructure import Session


class PostgresSession(Session):
    def execute(self, operation: object) -> object: ...
    def query(self, operation: object) -> object: ...
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def is_dirty(self) -> bool: ...
```

### Projections

Read and write models for querying and persisting data. Projections are use-case-like classes with `read()` and `write()` methods.

- `ReadProjection` — query data via `read(model: ReadModel)`
- `WriteProjection` — persist data via `write(model: WriteModel)`
- `Projection` — combines both read and write
- Async variants available (`AsyncReadProjection`, `AsyncWriteProjection`, `AsyncProjection`)

```python
from aod.infrastructure import ReadProjection, ReadModel


class UserListProjection(ReadProjection):
    def read(self, model: ReadModel) -> list[User]:
        return self.session.query("SELECT * FROM users")
```

### Containers

Dependency injection containers that wire ports to their implementations.

- `AdapterContainerBase` — declare ports as fields, infrastructure fills them
- `inject_adapters()` — creates a use case with ports wired from the container

```python
from aod.infrastructure import AdapterContainerBase, inject_adapters


class AppContainer(AdapterContainerBase):
    order_client: OrderClient


container = AppContainer(order_client=RealOrderClient())
use_case = inject_adapters(container, PlaceOrder)
```

## Next Steps

- [Quick Start](quickstart.md) — Apply these concepts in a working example
- [Domain Objects](../domain/index.md) — Detailed API for entities, value objects, and services
- [Application Layer](../application/index.md) — Use cases, ports, and contracts
- [Infrastructure](../infrastructure/index.md) — Sessions, projections, and containers