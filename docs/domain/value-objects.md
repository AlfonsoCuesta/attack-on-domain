# ValueObject

Value Objects are immutable, identity-less domain objects. They are defined by their attributes rather than by a unique identifier. Two value objects with the same field values are considered equal.

> **Note:** [EntityId](entity-id.md) is a specialized `ValueObject` — it is immutable and compared by value, but it serves as the identity for entities rather than data.

## Class Definition

`ValueObject` is always immutable — there is no way to change a value object after construction.

```python
from aod.domain import ValueObject


class Money(ValueObject):
    amount: float
    currency: str
```

## Constructor Parameters

`ValueObject.__init__()` accepts keyword arguments for every annotated field on the subclass. The constructor validates all values using the validation model (Pydantic with constraints and invariants).

```python
price = Money(amount=9.99, currency="USD")
```

Each annotated field becomes a constructor parameter:

| Parameter | Type | Description |
|-----------|------|-------------|
| `amount` | `float` | Monetary amount. Required unless a default is provided |
| `currency` | `str` | Currency code (e.g. `"USD"`). Required unless a default is provided |

Fields without defaults are required. Fields with defaults are optional:

```python
class Config(ValueObject):
    host: str = "localhost"
    port: int = 8080
    debug: bool = False

config = Config()
assert config.host == "localhost"
```

## Key Characteristics

### Immutable

Value objects cannot be changed after creation. Any attempt to set an attribute raises `MutationForbiddenException`:

```python
price.amount = 10.0  # MutationForbiddenException!
```

Unlike entities (which allow mutation inside public methods), value objects block mutation unconditionally:

```python
class Address(ValueObject):
    street: str
    city: str
    country: str

addr = Address(street="123 Main St", city="Springfield", country="US")
addr.city = "Shelbyville"  # MutationForbiddenException!
```

### No Identity

Value objects have no `id` field. They are compared by their attributes:

```python
class Email(ValueObject):
    value: str

e1 = Email(value="alice@example.com")
e2 = Email(value="alice@example.com")
assert e1 == e2  # True — same value, same object
```

### Structural Equality

Two value objects with the same attributes are considered equal:

```python
class Color(ValueObject):
    r: int
    g: int
    b: int

red1 = Color(r=255, g=0, b=0)
red2 = Color(r=255, g=0, b=0)
assert red1 == red2  # True

green = Color(r=0, g=255, b=0)
assert red1 != green  # True
```

## Default Values and Optional Fields

Default values make constructor parameters optional:

```python
from typing import Optional


class Address(ValueObject):
    street: str
    city: str
    country: str
    postal_code: Optional[str] = None

addr = Address(street="123 Main St", city="Springfield", country="US")
assert addr.postal_code is None
```

## Complex Value Objects

Value objects can contain other value objects:

```python
class Money(ValueObject):
    amount: float
    currency: str

class OrderTotal(ValueObject):
    subtotal: Money
    tax: Money
    total: Money

total = OrderTotal(
    subtotal=Money(amount=100.0, currency="USD"),
    tax=Money(amount=8.0, currency="USD"),
    total=Money(amount=108.0, currency="USD"),
)
```

## Type Hints

Value objects support all Python type hints, including collections, Optional, datetime, and nested value objects:

```python
from datetime import datetime
from typing import Optional


class AuditInfo(ValueObject):
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: str
    version: int = 1
```

## Validation with Pydantic

Value objects can use `@field_invariance` for field-level validation:

```python
from aod.domain.validation import field_invariance


class Money(ValueObject):
    amount: float
    currency: str

    @field_invariance("amount")
    def amount_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("amount must be positive")
        return v

price = Money(amount=-10.0, currency="USD")  # InvarianceException!
```

## Reconstruct

`reconstruct()` is a classmethod that creates value objects without validation. Useful for loading persisted data where validation has already been applied.

```python
money = Money.reconstruct(amount=9.99, currency="USD")
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `**kwargs` | `Any` | Same keyword arguments as the constructor, but validation is skipped |

## `__post_init__` Hook

Override `__post_init__()` for initialisation logic after all fields are set. It runs during normal `__init__` but NOT during `reconstruct()`.

```python
class Email(ValueObject):
    value: str

    def __post_init__(self):
        self._event_emitter.emit(EmailCreatedEvent(value=self.value))
```

### When to Use `__post_init__` vs `@field_invariance`

Both run at construction time but serve different purposes:

| Concern | `__post_init__` | `@field_invariance` |
|---------|-----------------|---------------------|
| What it does | Post-construction logic using the **instantiated object** (`self`) | Validates a **field value** before it is stored |
| Use case | Emit creation events, compute derived data | Enforce business rules on field values |
| Runs on `reconstruct()` | **No** — only on normal `__init__` | **No** |
| Has `self` | Yes | No — receives `cls` and the raw value |
| Can mutate fields | Yes (during the hook) | No |

**Use `__post_init__`** for operations that need the constructed instance. **Use `@field_invariance`** to validate that a value satisfies a domain rule before it is accepted.

## Testing

### `build()`

```python
from aod.testing import build

money = build(Money, amount=9.99, currency="USD")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `cls` | `type[T]` | The value object class to instantiate |
| `**kwargs` | `Any` | Field values. Same as constructor but validation is skipped |

### `events_of()`

```python
from aod.testing import events_of

events = events_of(money)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `obj` | `ValueObject` | The value object to extract events from |

Returns `list[Event]`.

## Common Patterns

### Money

```python
class Money(ValueObject):
    amount: float
    currency: str

    def add(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)
```

### Email

```python
class Email(ValueObject):
    value: str

    @field_invariance("value")
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email")
        return v.lower()
```

### DateRange

```python
from datetime import datetime
from aod.domain.validation import invariance


class DateRange(ValueObject):
    start: datetime
    end: datetime

    @invariance
    def end_after_start(cls, data: dict) -> dict:
        if data["end"] <= data["start"]:
            raise ValueError("end must be after start")
        return data
```

## Exceptions

| Exception | Raised When |
|-----------|-------------|
| `MutationForbiddenException` | Attempting to mutate a value object field after construction |
| `ModelValidationError` | Pydantic validation fails during `__init__` |

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="entities.md">Entity & RootEntity</a></h3>
<p>Learn about mutable domain objects with identity</p>
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
<h3><a href="validation.md">Validation</a></h3>
<p>Learn about invariants and validators</p>
</div>

</div>