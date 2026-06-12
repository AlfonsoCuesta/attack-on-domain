# Service

Services are stateless domain operations that encapsulate business logic that does not naturally belong to a single entity or value object.

## Class Definition

`Service` inherits from `BaseBehaviour`, which extends `BaseGuarded`. This means services can have state (fields) and mutate them inside public methods, but mutation from outside is blocked.

```python
from aod.domain import Service


class TaxCalculator(Service):
    def calculate_tax(self, amount: float, tax_rate: float) -> float:
        return amount * tax_rate

calculator = TaxCalculator()
tax = calculator.calculate_tax(100.0, 0.08)
assert tax == 8.0
```

## Constructor Parameters

`Service` has no special constructor parameters defined by the framework. You define your own fields via type annotations, and they become constructor parameters.

```python
class PricingService(Service):
    tax_rate: float
    discount_rate: float = 0.0

service = PricingService(tax_rate=0.08)
```

Each annotated field becomes a constructor parameter:

| Parameter | Type | Description |
|-----------|------|-------------|
| `tax_rate` | `float` | Tax rate applied to calculations. Required |
| `discount_rate` | `float` | Discount rate. Defaults to `0.0`, so it is optional |

Fields without defaults are required. Fields with defaults are optional.

## Stateful Services

Unlike entities, services are typically stateless, but they can hold mutable state:

```python
class CounterService(Service):
    count: int = 0

    def increment(self) -> None:
        self.count += 1

    def get_count(self) -> int:
        return self.count

counter = CounterService()
counter.increment()
assert counter.get_count() == 1
```

### Mutation Rules

Same as `BaseGuarded`:

- **Inside public methods**: Mutation is allowed (PASS state)
- **Outside methods**: Mutation is blocked. `MutationForbiddenException` is raised
- **During `__init__`**: Mutation is allowed (INHERIT state)

```python
counter.count = 5  # MutationForbiddenException!
```

## Event Emission

Services can emit domain events via `_event_emitter`. This is a `PrivateField(default_factory=EventEmitter)` available on every `Service` instance.

```python
from aod.events import Event


class OrderProcessed(Event):
    order_id: str


class OrderService(Service):
    def process_order(self, order_id: str) -> None:
        self._event_emitter.emit(OrderProcessed(order_id=order_id))
```

### `_event_emitter` Parameters

`_event_emitter.emit()` takes one parameter:

| Parameter | Type | Description |
|-----------|------|-------------|
| `event` | `Event` | An Event subclass instance to emit |

`_event_emitter.poll_events()` returns all collected events without clearing them:

| Parameter | Type | Description |
|-----------|------|-------------|
| (none) | — | — |

Returns `list[Event]`.

## Service Method Type Constraints

When a `Service` is registered in a `BoundedContext`, its public methods are inspected. The type checker (`ServiceTypeHandler.check_service`) validates that:

- **Allowed** parameter/return types: custom classes, `RootEntity`, `ValueObject`, primitives
- **Forbidden** parameter/return types: non-root `Entity` (raises `InvalidServiceParameterError`)

```python
class UserService(Service):
    def get_user(self, user_id: str) -> User:  # InvalidServiceParameterError!
        pass
```

Allowed usage:

```python
from aod.domain import RootEntity, Service


class User(RootEntity):
    id: str


class UserService(Service):
    def get_user(self, user_id: str) -> User:
        return User(id=user_id)
```

## Private Methods

Services can define private methods (prefixed with `_`). These are not wrapped with mutation context management — they execute within whatever context the caller provides.

```python
class ValidationService(Service):
    def _validate_email(self, email: str) -> bool:
        return "@" in email

    def validate_user(self, name: str, email: str) -> bool:
        if not self._validate_email(email):
            return False
        return len(name) > 0
```

## Type Hints

Services support all Python type hints:

```python
from typing import Optional
from datetime import datetime


class AuditService(Service):
    def log_action(
        self,
        user_id: str,
        action: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        if timestamp is None:
            timestamp = datetime.now()
        print(f"{timestamp}: {user_id} performed {action}")
```

## Testing

### `build()`

```python
from aod.testing import build

service = build(TaxCalculator)
tax = service.calculate_tax(100.0, 0.08)
assert tax == 8.0
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `cls` | `type[T]` | The service class to instantiate |
| `**kwargs` | `Any` | Field values. Validation is skipped |

### `events_of()`

```python
from aod.testing import events_of

service = build(OrderService)
service.process_order("order-1")
events = events_of(service)
assert len(events) == 1
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `obj` | `BaseGuarded` | The service to extract events from |

Returns `list[Event]`.

## Common Patterns

### Domain Service

```python
class PricingService(Service):
    def calculate_total(self, items: list[OrderItem]) -> float:
        return sum(item.price * item.quantity for item in items)
```

### Validation Service

```python
class OrderValidator(Service):
    def validate_order(self, order: Order) -> bool:
        if not order.items:
            return False
        if order.total < 0:
            return False
        return True
```

### Notification Service

```python
class NotificationService(Service):
    def notify_user(self, user: User, message: str) -> None:
        pass
```

### Service with Events

```python
class ShipmentService(Service):
    def ship_order(self, order: Order) -> None:
        self._event_emitter.emit(OrderShipped(order_id=order.id))
```

## Exceptions

| Exception | Raised When |
|-----------|-------------|
| `MutationForbiddenException` | Attempting to mutate a service field outside a public method |
| `InvalidServiceParameterError` | Service method parameter or return type is a non-root `Entity` |

## Next Steps

- [Entity & RootEntity](entities.md) — Learn about mutable domain objects
- [ValueObject](value-objects.md) — Learn about immutable domain objects
- [Event System](events.md) — Learn about emitting events from services
- [Bounded Context](bounded-context.md) — Learn about registering services