# Entity & RootEntity

Entities are mutable domain objects with a distinct identity. Two entities with different identities are always different, regardless of their attribute values. Entities compare by their `EntityId` only — `==` checks identity, not field values.

## Entity

`Entity` is the base class for all domain objects that have identity, mutation guards, event emission, and validation. Every entity must have exactly one [EntityId](entity-id.md) field — the framework enforces this at class creation time.

### Class Definition

```python
from aod.domain import Entity
from aod.domain import EntityId


class UserId(EntityId):
    value: str


class User(Entity):
    id: UserId
    name: str
    email: str
```

### Constructor Parameters

`Entity.__init__()` accepts keyword arguments for every field defined on the subclass. Fields are generated from type annotations.

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | `UserId` | Entity identity — must be an `EntityId` subclass. Required |
| `name` | `str` | Field derived from class annotation. Required unless optional or defaulted |
| `email` | `str` | Field derived from class annotation. Required unless optional or defaulted |

Each annotated field becomes a constructor parameter. Fields without defaults are required. Fields with defaults (e.g. `name: str = "unnamed"`) are optional.

```python
user = User(id=UserId(value="abc"), name="Alice", email="alice@example.com")

# Entities have identity — two entities with the same id are equal
user2 = User(id=UserId(value="abc"), name="Alice", email="alice@example.com")
assert user == user2
```

### Field Utility: `Field()`

```python
from aod.domain import Field
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `default` | `Any` | `...` | Default value for the field |
| `default_factory` | `Callable[[], Any] \| None` | `None` | Callable that produces the default value each time |
| `gt` | `SupportsGt \| None` | `None` | Greater-than constraint for numeric fields |
| `ge` | `SupportsGe \| None` | `None` | Greater-than-or-equal constraint |
| `lt` | `SupportsLt \| None` | `None` | Less-than constraint |
| `le` | `SupportsLe \| None` | `None` | Less-than-or-equal constraint |
| `multiple_of` | `float \| None` | `None` | Value must be a multiple of this number |
| `strict` | `bool \| None` | `None` | Enforce strict type checking |
| `min_length` | `int \| None` | `None` | Minimum string length |
| `max_length` | `int \| None` | `None` | Maximum string length |
| `pattern` | `str \| Pattern \| None` | `None` | Regex pattern for string validation |
| `allow_inf_nan` | `bool \| None` | `None` | Allow infinity or NaN values |
| `max_digits` | `int \| None` | `None` | Maximum number of digits (decimal) |
| `decimal_places` | `int \| None` | `None` | Maximum decimal places |
| `id` | `bool` | `False` | When `True`, marks this field as the entity identity. Must be an `EntityId` subclass. Only allowed on Entity/RootEntity, not ValueObject |

### Identity Field

Every `Entity` / `RootEntity` subclass must have exactly one identity field. Use `Field(id=True)` to mark it explicitly when you have multiple `EntityId`-typed fields:

```python
class User(RootEntity):
    id: UserId = Field(id=True)
    father: UserId  # reference, not the identity
```

Without `Field(id=True)`, the framework falls back to finding a single `EntityId` field automatically. If zero or multiple `EntityId` fields are found, a `NoEntityIdException` or `TooManyEntityIdsException` is raised.

### PrivateField

```python
from aod.domain import PrivateField
```

| Overload | Parameter | Type | Description |
|----------|-----------|------|-------------|
| Positional | `default` | `Any` | Default value for the private field |
| Keyword | `default_factory` | `Callable[[], Any]` | Callable producing the default value each time |

`PrivateField` creates Pydantic private attributes that are not included in the constructor, serialization, or equality checks.

```python
class User(Entity):
    id: UserId
    name: str
    _password_hash: str = PrivateField(default="")

    def set_password(self, password: str) -> None:
        self._password_hash = hash_password(password)
```

### Mutation Rules

- **Inside public methods**: Fields can be assigned.
- **Outside methods**: Mutation is blocked. `MutationForbiddenException` is raised.
- **During `__init__`**: Mutation is allowed.

```python
class User(Entity):
    id: UserId
    name: str

    def rename(self, new_name: str) -> None:
        self.name = new_name

user = User(id=UserId(value=1), name="Alice")
user.rename("Bob")
assert user.name == "Bob"

user.name = "Charlie"  # MutationForbiddenException!
```

### `can_mutate()`

Every entity exposes a public `can_mutate()` method that controls whether mutation is allowed inside its own methods. By default it returns `True`, allowing mutation inside public methods. Subclasses can override it to conditionally block mutation:

```python
from aod.domain import PrivateField
from aod.domain.validation import mutable


class User(RootEntity):
    id: UserId
    name: str
    _locked: bool = PrivateField(default=False)

    def can_mutate(self) -> bool:
        return not self._locked

    @mutable
    def lock(self) -> None:
        self._locked = True

    @mutable
    def unlock(self) -> None:
        self._locked = False

    def rename(self, new_name: str) -> None:
        self.name = new_name

user = User(id=UserId(value="1"), name="Alice")
user.rename("Bob")           # OK

user.lock()
user.rename("Charlie")       # MutationForbiddenException!

user.unlock()
user.rename("Dave")          # OK again
```

`lock()` and `unlock()` use `@mutable` so they bypass the `can_mutate()` guard. Without it, `unlock()` would fail because the entity is locked and mutation is blocked.

When `can_mutate()` returns `False`, any attempt to mutate the entity (set fields, append to lists, etc.) raises `MutationForbiddenException`. This applies both inside and outside methods.

The private `_can_mutate()` (used internally by the framework's mutation guard) delegates to `can_mutate()`, so overriding `can_mutate()` is the only hook needed.

### Immutable Proxies

When reading field values outside a mutation context, mutable containers are wrapped in immutable proxies:

- `list` becomes `ImmutableList` (blocks `append`, `extend`, `__setitem__`)
- `dict` becomes `ImmutableDict` (blocks `__setitem__`, `update`, `pop`)
- `set` becomes `ImmutableSet` (blocks `add`, `remove`, `discard`)

```python
class User(Entity):
    id: UserId
    tags: list[str]

user = User(id=UserId(value=1), tags=["admin", "user"])
user.tags.append("super")  # MutationForbiddenException!
```

Inside a method, the real mutable objects are available:

```python
class User(Entity):
    id: UserId
    tags: list[str]

    def add_tag(self, tag: str) -> None:
        self.tags.append(tag)  # Works inside method
```

### Type Hints

Entities support all Python type hints:

```python
from typing import Optional
from datetime import datetime


class User(Entity):
    id: UserId
    name: str
    email: str
    created_at: datetime
    last_login: Optional[datetime] = None
    tags: list[str] = Field(default_factory=list)
```

## RootEntity

`RootEntity` is an entity that serves as an aggregate root. It is the entry point to a cluster of associated domain objects and cannot be nested inside other entities.

```python
from aod.domain import RootEntity, ValueObject


class OrderId(EntityId):
    value: int


class OrderLine(ValueObject):
    product_id: str
    quantity: int
    price: float


class Order(RootEntity):
    id: OrderId
    lines: list[OrderLine]
    total: float

    def add_line(self, product_id: str, quantity: int, price: float) -> None:
        line = OrderLine(product_id=product_id, quantity=quantity, price=price)
        self.lines.append(line)
        self.total += quantity * price
```

### Constructor Parameters

`RootEntity.__init__()` accepts the same keyword arguments pattern as `Entity`. Each annotated field becomes a constructor parameter.

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | `OrderId` | Root entity identity — must be an `EntityId` subclass |
| `lines` | `list[OrderLine]` | Field derived from class annotation |
| `total` | `float` | Field derived from class annotation |

### Nesting Restrictions

RootEntity is flagged so that `BoundedContext` rejects any Entity or ValueObject field that references a `RootEntity` subclass. This prevents aggregate roots from being nested inside other objects — a DDD best practice.

Allowed: reference by ID instead of by object:

```python
class Order(RootEntity):
    id: OrderId
    user_id: str  # OK
```

Forbidden: direct nesting:

```python
class Order(RootEntity):
    id: OrderId
    user: User  # InvalidNestedTypeError!
```

### Why Use RootEntity

- **Consistency boundaries** — Changes to the aggregate must go through the root
- **Bounded Context enforcement** — Root entities are the top-level types registered in `BoundedContext`
- **Event collection** — Events from child entities are collected through the root

## Reconstruct

`reconstruct()` is a classmethod that creates entities without validation, making it suitable for loading persisted objects from a database.

```python
user = User.reconstruct(id=UserId(value=1), name="Alice")
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `**kwargs` | `Any` | Same keyword arguments as the constructor, but validation is skipped |

The `__post_init__` hook does NOT run during `reconstruct()`, only during normal `__init__`.

## `__post_init__` Hook

Override `__post_init__` to run initialization logic after all fields are set. It runs during normal construction, not during `reconstruct()`.

```python
class User(RootEntity):
    id: UserId
    name: str

    def __post_init__(self):
        self._event_emitter.emit(UserCreatedEvent(user_id=self.id.value))
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| (none) | — | No parameters. All fields are already set before this hook runs |

During `__post_init__`, public methods can be called and fields can be mutated.

### When to Use `__post_init__` vs `@invariance` / `@field_invariance`

Both hooks run at construction time, but they serve different purposes.

| Concern | `__post_init__` | `@invariance` / `@field_invariance` |
|---------|-----------------|--------------------------------------|
| What it does | Post-construction logic using the **already-initialized instance** (`self`) | Validates field or model **values** before they are stored |
| Use case | Emit creation events, compute derived values, call setup methods | Check business rules: "quantity must be positive", "end date must be after start" |
| Runs on `reconstruct()` | **No** — only on normal `__init__` | **No** — only on normal `__init__` |
| Has access to `self` | Yes — all fields are set | No — receives `cls` and the raw value |
| Can mutate fields | Yes (during the hook) | No — read-only |

**Use `__post_init__` when you need to:**

- Emit a domain event at creation time
- Compute a derived field that depends on other fields
- Call a setup/initialization method
- Perform any operation that needs the full constructed instance

```python
class User(RootEntity):
    id: UserId
    name: str
    created_at: datetime

    def __post_init__(self):
        self._event_emitter.emit(UserCreated(user_id=self.id.value))
        self.created_at = datetime.now(timezone.utc)
```

**Do NOT override `__init__`** directly — use `__post_init__` instead. The framework's `__init__` handles validation, model construction, and mutation context setup before calling this hook.

**Use `@invariance` / `@field_invariance` when you need to:**

- Validate that a field satisfies a domain rule
- Reject invalid states at construction time
- Validate relationships between fields

```python
class Money(ValueObject):
    amount: float
    currency: str

    @field_invariance("amount")
    def amount_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("amount must be positive")
        return v
```

> **Rule of thumb:** if the check can be expressed as "this value must satisfy X", use `@field_invariance`. If the check needs the constructed instance (you need `self`), use `__post_init__`.

## Testing

Testing utilities are available from `aod.testing`:

### `build()`

```python
from aod.testing import build

user = build(User, id=UserId(value=1), name="Alice")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `cls` | `type[T]` | The domain class to instantiate |
| `**kwargs` | `Any` | Field values. Same as constructor but validation is skipped |

### `events_of()`

```python
from aod.testing import events_of

events = events_of(user)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `obj` | `Entity \| ValueObject \| Service` | The domain object to extract events from |

Returns `list[Event]` — all events emitted by this object.

### `assert_event_emitted()`

```python
from aod.testing import assert_event_emitted

assert_event_emitted(events, UserRegistered, user_id="1")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `events` | `Sequence[Event]` | Sequence of events to search (from `events_of()`) |
| `event_type` | `type[Event]` | The expected event class |
| `**attrs` | `Any` | Key-value pairs of expected attribute values on the event |

Raises `AssertionError` if no matching event is found.

### `assert_no_events()`

```python
from aod.testing import assert_no_events

assert_no_events(events)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `events` | `Sequence[Event]` | Sequence of events to check |

Raises `AssertionError` if the sequence is non-empty.

## Common Patterns

### Constructor with Defaults

```python
class User(Entity):
    id: UserId
    name: str
    role: str = "member"
    is_active: bool = True
```

### Entity with Events

```python
from aod.events import Event


class UserRegistered(Event):
    user_id: int
    email: str


class User(RootEntity):
    id: UserId
    email: str

    def register(self) -> None:
        self._event_emitter.emit(UserRegistered(user_id=self.id.value, email=self.email))
```

### Entity with Value Object Fields

```python
class Address(ValueObject):
    street: str
    city: str
    country: str


class User(Entity):
    id: UserId
    name: str
    address: Address
```

## Exceptions

| Exception | Raised When |
|-----------|-------------|
| `MutationForbiddenException` | Attempting to mutate an entity field outside a public method |
| `NoEntityIdException` | An `Entity` or `RootEntity` subclass has no `EntityId` field |
| `TooManyEntityIdsException` | An `Entity` or `RootEntity` subclass has more than one `EntityId` field |
| `InvalidIdentityFieldTypeError` | `Field(id=True)` is used on a field that is not an `EntityId` subclass |
| `InvalidNestedTypeError` | An Entity or ValueObject field references a RootEntity |
| `ModelValidationError` | Pydantic validation fails during construction |

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="entity-id.md">EntityId</a></h3>
<p>Learn about entity identity</p>
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
<p>Learn about organizing aggregates</p>
</div>

</div>