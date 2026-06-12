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
<h3>Bounded Context</h3>
<p>Organise your domain into type-safe boundaries with automatic entity/value object discovery.</p>
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

## Quick Example

```python
from aod.domain import RootEntity, ValueObject, Event
from aod.application import UseCase, Port

class OrderId(ValueObject):
    value: str

class Order(RootEntity):
    id: OrderId
    total: float

class OrderPlaced(Event):
    order_id: str
    total: float

class OrderClient(Port):
    def save(self, order: Order) -> None: ...

class PlaceOrder(UseCase):
    order_client: OrderClient

    def run(self, order_id: str, total: float) -> None:
        order = Order(id=OrderId(value=order_id), total=total)
        self.order_client.save(order)
        self._event_emitter.emit(OrderPlaced(order_id=order_id, total=total))
```

## Architecture

The library follows a layered DDD architecture:

| Layer | Components | Depends On |
|-------|-----------|------------|
| **Infrastructure** | Projections, Sessions, Container | Application |
| **Application** | UseCase, Ports, Contracts | Domain |
| **Domain** | Entity, ValueObject, Service | - (pure business logic) |

Each layer depends only on the layer below it:

- **Domain** — Pure business logic with no infrastructure dependencies
- **Application** — Orchestrates domain objects through Port interfaces
- **Infrastructure** — Implements ports for databases, APIs, and other external systems

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3>Quick Start</h3>
<p>Get up and running in 5 minutes with a complete example.</p>
<p><a href="getting-started/quickstart/">Quick Start</a></p>
</div>

<div class="feature-card">
<h3>DDD Concepts</h3>
<p>Learn the Domain-Driven Design principles behind the library.</p>
<p><a href="getting-started/concepts/">Concepts</a></p>
</div>

<div class="feature-card">
<h3>Building Blocks</h3>
<p>Entities, Value Objects, Services, and more.</p>
<p><a href="domain/entities/">Domain</a></p>
</div>

<div class="feature-card">
<h3>Testing</h3>
<p>Utilities for testing your domain, application, and infrastructure.</p>
<p><a href="testing/">Testing</a></p>
</div>

</div>
