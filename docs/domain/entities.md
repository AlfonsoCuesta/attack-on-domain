# Entity & RootEntity

Entities are mutable domain objects with a distinct identity. Two entities with the same attribute values are still different entities if they are separate instances.

## Entity

`Entity` is the base class for all domain objects that have identity. It inherits from `ReconstructMixin` and `BaseGuarded`, which provides mutation guards, event emission, and the validation system.

### Class Definition

```python
from aod.domain import Entity


class User(Entity):
    id: str
    name: str
    email: str
```

### Constructor Parameters

`Entity.__init__()` accepts keyword arguments for every field defined on the subclass. Fields are generated from type annotations.

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Entity identity field. Required unless a default is provided |
| `name` | `str` | Field derived from class annotation. Required unless optional or defaulted |
| `email` | `str` | Field derived from class annotation. Required unless optional or defaulted |

Each annotated field becomes a constructor parameter. Fields without defaults are required. Fields with defaults (e.g. `name: str = "unnamed"`) are optional.

```python
user = User(id="1", name="Alice", email="alice@example.com")

# Entities have identity — different instances are never equal
user2 = User(id="1", name="Alice", email="alice@example.com")
assert user != user2
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
| `init` | `bool` | `True` | Whether the field accepts a value at construction time |

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
    id: str
    name: str
    _password_hash: str = PrivateField(default="")

    def set_password(self, password: str) -> None:
        self._password_hash = hash_password(password)
```

### Mutation Rules

Entities follow the `BaseGuarded` mutation policy:

- **Inside public methods**: Mutation is allowed (PASS state). Fields can be assigned.
- **Outside methods**: Mutation is blocked. `MutationForbiddenException` is raised.
- **During `__init__`**: Mutation is allowed (INHERIT state) during construction.

```python
class User(Entity):
    id: str
    name: str

    def rename(self, new_name: str) -> None:
        self.name = new_name

user = User(id="1", name="Alice")
user.rename("Bob")
assert user.name == "Bob"

user.name = "Charlie"  # MutationForbiddenException!
```

### Immutable Proxies

When reading field values outside a mutation context, mutable containers are wrapped in immutable proxies:

- `list` becomes `ImmutableList` (blocks `append`, `extend`, `__setitem__`)
- `dict` becomes `ImmutableDict` (blocks `__setitem__`, `update`, `pop`)
- `set` becomes `ImmutableSet` (blocks `add`, `remove`, `discard`)

```python
class User(Entity):
    id: str
    tags: list[str]

user = User(id="1", tags=["admin", "user"])
user.tags.append("super")  # MutationForbiddenException!
```

Inside a method, the real mutable objects are available:

```python
class User(Entity):
    id: str
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
    id: str
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


class OrderLine(ValueObject):
    product_id: str
    quantity: int
    price: float


class Order(RootEntity):
    id: str
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
| `id` | `str` | Root entity identity field |
| `lines` | `list[OrderLine]` | Field derived from class annotation |
| `total` | `float` | Field derived from class annotation |

### Nesting Restrictions

RootEntity is flagged so that `BoundedContext` rejects any Entity or ValueObject field that references a `RootEntity` subclass. This prevents aggregate roots from being nested inside other objects — a DDD best practice.

Allowed: reference by ID instead of by object:

```python
class Order(RootEntity):
    id: str
    user_id: str  # OK
```

Forbidden: direct nesting:

```python
class Order(RootEntity):
    id: str
    user: User  # InvalidNestedTypeError!
```

### Why Use RootEntity

- **Consistency boundaries** — Changes to the aggregate must go through the root
- **Bounded Context enforcement** — Root entities are the top-level types registered in `BoundedContext`
- **Event collection** — Events from child entities are collected through the root

## Reconstruct

`reconstruct()` is a classmethod available on `Entity` and `RootEntity` (via `ReconstructMixin`). It creates instances without running Pydantic validation, making it suitable for loading persisted objects from a database.

```python
user = User.reconstruct(id="1", name="Alice")
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `**kwargs` | `Any` | Same keyword arguments as the constructor, but validation is skipped |

The `__post_init__` hook does NOT run during `reconstruct()`, only during normal `__init__`.

## `__post_init__` Hook

Defined as an empty method on `BaseValidator`. Override it to run initialization logic after all fields are set. It only runs during normal construction, not during `reconstruct()`.

```python
class User(RootEntity):
    id: int
    name: str

    def __post_init__(self):
        self._event_emitter.emit(UserCreatedEvent(user_id=self.id))
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| (none) | — | No parameters. All fields are already set via `__set_model_attributes` before this hook runs |

During `__post_init__`, the mutation context is in INHERIT state, so public methods can be called and fields can be mutated.

## Testing

Testing utilities are available from `aod.testing`:

### `build()`

```python
from aod.testing import build

user = build(User, id="1", name="Alice")
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
| `obj` | `BaseGuarded` | The entity or domain object to extract events from |

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
    id: str
    name: str
    role: str = "member"
    is_active: bool = True
```

### Entity with Events

```python
from aod.events import Event


class UserRegistered(Event):
    user_id: str
    email: str


class User(RootEntity):
    id: str
    email: str

    def register(self) -> None:
        self._event_emitter.emit(UserRegistered(user_id=self.id, email=self.email))
```

### Entity with Value Object Fields

```python
class Address(ValueObject):
    street: str
    city: str
    country: str


class User(Entity):
    id: str
    name: str
    address: Address
```

## Exceptions

| Exception | Raised When |
|-----------|-------------|
| `MutationForbiddenException` | Attempting to mutate an entity field outside a public method |
| `InvalidNestedTypeError` | An Entity or ValueObject field references a RootEntity |
| `ModelValidationError` | Pydantic validation fails during construction |

## Next Steps

- [ValueObject](value-objects.md) — Learn about immutable domain objects
- [Service](services.md) — Learn about stateless domain operations
- [Event System](events.md) — Learn about domain events
- [Bounded Context](bounded-context.md) — Learn about organizing aggregates
