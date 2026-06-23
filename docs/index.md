# attack-on-domain

<div class="home-hero">
<div class="hero-title-row">
<img src="img/dark-logo.png" alt="attack-on-domain" class="hero-logo">
<h1>attack-on-domain</h1>
</div>
<p class="subtitle">DDD building blocks for Python 3.14+</p>
<p class="description">
Build maintainable domain models with entities, value objects, aggregates, CQRS, and hexagonal architecture — fully typed, immutable, with built-in validation, and designed for real-world applications.
</p>
<div class="install-code">pip install attack-on-domain</div>
</div>

## Key Features

<div class="home-features">

<div class="feature-card">
<h3>Domain Building Blocks</h3>
<p>Entity, RootEntity, ValueObject, and Aggregate — everything you need to model your business domain with identity, mutation guards, and consistency boundaries.</p>
</div>

<div class="feature-card">
<h3>Domain Events</h3>
<p>Immutable, auto-timestamped records of domain occurrences. Automatically collected by use cases.</p>
</div>

<div class="feature-card">
<h3>CQRS</h3>
<p>CQRS-based architecture with easy-to-implement commands, queries, and handlers.</p>
</div>

<div class="feature-card">
<h3>Use Cases</h3>
<p>Application-layer operations with auto-wired ports, event collection, logging, and transaction management.</p>
</div>

<div class="feature-card">
<h3>Business Invariants</h3>
<p>Enforce domain rules at construction time with type-safe field and model-level invariants that raise clear domain exceptions.</p>
</div>

<div class="feature-card">
<h3>Testing</h3>
<p>Spy containers, session stubs, fakers, and event assertions — everything you need to test your domain, application, and infrastructure layers.</p>
</div>

</div>

## Quick Example — Use Case with CQRS and Dependency Injection

```python
from aod.domain import RootEntity, ValueObject, Event
from aod.application import UseCase, Command, CommandPort
from aod.infrastructure import CommandHandler, Session, AdapterContainer


class SqlSession(Session):
    def execute(self, operation: object) -> None: ...

class OrderId(ValueObject):
    value: str

class Order(RootEntity):
    id: OrderId
    total: float

class OrderPlaced(Event):
    order_id: str
    total: float

class PlaceOrder(Command[Order, None]):
    order_id: str
    total: float

class PlaceOrderHandler(CommandHandler[PlaceOrder]):
    session: SqlSession

    def handle(self, command: PlaceOrder) -> None:
        order = Order(id=OrderId(value=command.order_id), total=command.total)
        self.session.execute(order)

class PlaceOrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]

    def run(self, order_id: str, total: float) -> None:
        self.place_order.handle(PlaceOrder(
            order_id=order_id, total=total,
        ))

container = AdapterContainer(handlers=[PlaceOrderHandler])
use_case = container.adapt_use_case(PlaceOrderUseCase)
use_case.run(order_id="1", total=99.99)
```

## Architecture

The library follows **hexagonal architecture** (ports and adapters) combined with DDD layers:

| Layer | Components | Depends On |
|-------|-----------|------------|
| **Infrastructure** | Handlers, Session, Container, Projection | Application |
| **Application** | UseCase, Port, Command, Query | Domain |
| **Domain** | Entity, ValueObject, Service, Event | None - (pure business logic) |

Each layer depends only on the layer below it:

- **Domain** — Pure business logic with no infrastructure dependencies
- **Application** — Orchestrates domain objects through Port interfaces
- **Infrastructure** — Implements ports for databases, APIs, and other external systems

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="getting-started/quickstart/">Quick Start</a></h3>
<p>Get up and running in 5 minutes with a complete example.</p>
</div>

<div class="feature-card">
<h3><a href="getting-started/concepts/">DDD Concepts</a></h3>
<p>Learn the Domain-Driven Design principles behind the library.</p>
</div>

<div class="feature-card">
<h3><a href="domain/entities/">Building Blocks</a></h3>
<p>Entities, Value Objects, Services, and more.</p>
</div>

<div class="feature-card">
<h3><a href="testing/">Testing</a></h3>
<p>Utilities for testing your domain, application, and infrastructure.</p>
</div>

</div>
