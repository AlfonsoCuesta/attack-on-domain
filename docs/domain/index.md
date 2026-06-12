# Domain Layer

The domain layer is the heart of your application. It contains the business logic, rules, and data structures that define your domain.

## Building Blocks

| Block | Description | Mutability |
|-------|-------------|------------|
| [Entity](entities.md) | Mutable object with identity | Mutable |
| [RootEntity](entities.md#rootentity) | Aggregate root entity | Mutable |
| [ValueObject](value-objects.md) | Immutable, identity-less object | Immutable |
| [Service](services.md) | Stateless domain operation | Stateless |
| [Event](events.md) | Record of something that happened | Immutable |
| [Validation](validation.md) | Type hints and validators | - |

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
from aod.domain import RootEntity, ValueObject, Event

# Value Object — immutable
class Money(ValueObject):
    amount: float
    currency: str

# Event — immutable, auto-timestamped
class OrderPlaced(Event):
    order_id: str
    total: float

# Root Entity — mutable, has identity
class Order(RootEntity):
    id: str
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
user = User(id="1", name="Alice")
user.name = "Bob"  # MutationForbiddenException!

# But inside methods:
class User(RootEntity):
    id: str
    name: str

    def rename(self, new_name: str) -> None:
        self.name = new_name  # Works!
```

### Immutable Proxies

When you read attributes outside a mutation context, you get immutable proxies:

```python
user = User(id="1", tags=["admin", "user"])
user.tags.append("super")  # MutationForbiddenException!
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

- [Entity & RootEntity](entities.md) — Learn about mutable domain objects
- [ValueObject](value-objects.md) — Learn about immutable domain objects
- [Service](services.md) — Learn about stateless domain operations
- [Event System](events.md) — Learn about domain events
- [Bounded Context](bounded-context.md) — Learn about organizing your domain
- [Validation](validation.md) — Learn about type hints and validators
