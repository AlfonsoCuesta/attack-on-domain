# attack-on-domain

<div class="home-hero">
<h1>attack-on-domain</h1>
<p class="subtitle">DDD building blocks for Python 3.14+</p>
<p class="description">
Entities, Value Objects, Bounded Contexts, Domain Events — all with full type safety and immutability guarantees, built on Pydantic v2.
</p>
<div class="install-code">pip install attack-on-domain</div>
</div>

## Key Features

<div class="home-features">

<div class="feature-card">
<h3>Entity & RootEntity</h3>
<p>Mutable domain objects with identity. Mutate fields inside public methods — immutable from outside.</p>
</div>

<div class="feature-card">
<h3>Value Object</h3>
<p>Immutable, identity-less objects compared by value. Perfect for Money, Email, Address, and other primitives.</p>
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
<h3>Validation</h3>
<p>Type-safe validation through Pydantic type hints and domain invariance rules to enforce business policies.</p>
</div>

</div>

## Quick Example — Use Case with CQRS and Dependency Injection

```python
from aod.domain import RootEntity, ValueObject, Event
from aod.application import UseCase, Command, CommandPort
from aod.infrastructure import CommandHandler, AdapterContainerBase, inject_adapters

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
    def handle(self, command: PlaceOrder) -> None:
        order = Order(id=OrderId(value=command.order_id), total=command.total)
        self.session.execute(order)

class PlaceOrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]

    def run(self, order_id: str, total: float) -> None:
        order = Order(id=OrderId(value=order_id), total=total)
        order.place()
        self.place_order.handle(PlaceOrder(
            order_id=order_id, total=total,
        ))

class AppContainer(AdapterContainerBase):
    handlers: list = [PlaceOrderHandler]

container = AppContainer()
use_case = inject_adapters(container, PlaceOrderUseCase)
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
