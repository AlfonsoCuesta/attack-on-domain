# Domain Layer

The domain layer is the heart of your application. It contains the business logic, rules, and data structures that define your domain.

## Building Blocks

| Block | Description | Mutability |
|-------|-------------|------------|
| [Entity](entities.md) | Mutable object with identity | Mutable |
| [RootEntity](entities.md#rootentity) | Aggregate root entity | Mutable |
| [Identity Field](entity-id.md) | Identity via `Field(id=True)` | - |
| [ValueObject](value-objects.md) | Immutable, identity-less object | Immutable |
| [Service](services.md) | Stateless domain operation | Stateless |
| [Event](events.md) | Record of something that happened | Immutable |
| [Invariants](validation.md) | Business rules enforced at construction (`@field_invariance`, `@invariance`) | - |

## Imports

```python
from aod.domain import (
    Entity,
    RootEntity,
    ValueObject,
    Service,
    Field,
    PrivateField,
    BoundedContext,
    DomainException,
)
from aod.events import Event, EventCollector
```

## Quick Example

```python
from aod.domain import RootEntity, ValueObject, Field
from aod.events import Event

# Value Object — immutable
class Money(ValueObject):
    amount: float
    currency: str

# Event — immutable, auto-timestamped
class OrderPlaced(Event):
    order_id: int
    total: float

# Root Entity — mutable, has identity
class Order(RootEntity):
    id: int = Field(id=True)
    total: Money

    def place(self) -> None:
        self._event_emitter.emit(
            OrderPlaced(order_id=self.id, total=self.total.amount)
        )
```

## Key Concepts

### Mutation Guards

Entities and Root Entities have automatic mutation guards:

- **Inside methods**: Mutation is allowed (PASS state)
- **Outside methods**: Mutation is blocked (BLOCK state)
- **During `__init__`**: Mutation is allowed (INHERIT state)

```python
class User(RootEntity):
    id: int = Field(id=True)
    name: str

    def rename(self, new_name: str) -> None:
        self.name = new_name  # Works!

user = User(id=1, name="Alice")
user.name = "Bob"  # MutationForbiddenException!
```

### Immutable Proxies

When you read attributes outside a mutation context, you get immutable proxies:

```python
user = User(id=1, tags=["admin", "user"])
user.tags.append("super")  # MutationForbiddenException!
```

### Business Invariants

Enforce domain rules at construction time with `@field_invariance` (field-level) and `@invariance` (model-level). Violations raise `InvarianceException`, a domain exception.

```python
from aod.domain.validation import field_invariance


class Money(ValueObject):
    amount: float
    currency: str

    @field_invariance("amount")
    def amount_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Amount must be positive")
        return v


Money(amount=-5.0, currency="USD")  # InvarianceException!
```

### Event Collection

Events are automatically collected across aggregate boundaries:

```python
from aod.events import EventCollector

with EventCollector() as events:
    order.place()
    order.ship()
# events contains OrderPlaced and OrderShipped
```

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="entities.md">Entity & RootEntity</a></h3>
<p>Learn about mutable domain objects</p>
</div>

<div class="feature-card">
<h3><a href="value-objects.md">ValueObject</a></h3>
<p>Learn about immutable domain objects</p>
</div>

<div class="feature-card">
<h3><a href="services.md">Service</a></h3>
<p>Learn about stateless domain operations</p>
</div>

<div class="feature-card">
<h3><a href="events.md">Event System</a></h3>
<p>Learn about domain events</p>
</div>

<div class="feature-card">
<h3><a href="bounded-context.md">Bounded Context</a></h3>
<p>Learn about organizing your domain</p>
</div>

<div class="feature-card">
<h3><a href="validation.md">Invariants</a></h3>
<p>Learn about business rules and validation</p>
</div>

</div>