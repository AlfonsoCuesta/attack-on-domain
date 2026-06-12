# Bounded Context

A Bounded Context is a boundary within which a particular domain model is defined and consistent. It organizes domain objects into logical groups and enforces type constraints at construction time.

## Class Definition

```python
from collections.abc import Iterable

from aod.domain import BoundedContext, RootEntity, Service


class User(RootEntity):
    id: str
    name: str

class UserService(Service):
    def get_user(self, user_id: str) -> User:
        return User(id=user_id)

context = BoundedContext(
    aggregate_roots=[User],
    services=[UserService],
    name="users",
)
```

## Constructor Parameters

```python
class BoundedContext:
    def __init__(
        self,
        aggregate_roots: Iterable[RootEntityType] | None = None,
        services: Iterable[ServiceType] | None = None,
        *,
        name: str | None = None,
    ) -> None: ...
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `aggregate_roots` | `Iterable[RootEntityType] \| None` | `None` | RootEntity subclasses that serve as aggregate roots in this context. Each must be a `RootEntity` subclass. Automatically discovers child entities and value objects through field type inspection |
| `services` | `Iterable[ServiceType] \| None` | `None` | Service subclasses that operate on this domain. Each must be a `Service` subclass. Method parameter and return types are validated for DDD compliance |
| `name` | `str \| None` | `None` | Optional human-readable name for the bounded context. Used in error messages and the `describe()` output |

### `aggregate_roots`

Type: `Iterable[RootEntityType] | None`

The aggregate roots define the entry points to the domain. The bounded context inspects all field types on each aggregate root (recursively) to discover child entities and value objects.

```python
class Address(ValueObject):
    street: str
    city: str

class User(RootEntity):
    id: str
    name: str
    address: Address

context = BoundedContext(aggregate_roots=[User])
# Automatically discovers: Address (ValueObject)
```

Validation:

- Each item must be a class (not an instance) — raises `ClassExpectedError` otherwise
- Each item must be a subclass of `Entity` — raises `InvalidEntityTypeError` otherwise
- Each item must be a subclass of `RootEntity` — raises `InvalidRootEntityTypeError` otherwise

### `services`

Type: `Iterable[ServiceType] | None`

Services registered in a bounded context have their public method signatures validated:

- Parameters and return types must not be non-root `Entity` subclasses
- Violations raise `InvalidServiceParameterError`

```python
class TaxCalculator(Service):
    def calculate(self, amount: float, rate: float) -> float:
        return amount * rate

context = BoundedContext(
    aggregate_roots=[Order],
    services=[TaxCalculator],
    name="billing",
)
```

### `name`

Type: `str | None`

An optional label for the context. Used in:

- `__repr__()` — returns the name if set
- `DuplicateDomainTypeError` messages — identifies which context a type already belongs to
- `describe()` output — keys are context names

```python
context = BoundedContext(aggregate_roots=[User], name="users")
print(context)  # users
```

## Instance Attributes

After construction, a `BoundedContext` exposes these read-only attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `aggregate_roots` | `tuple[RootEntityType, ...]` | Tuple of registered aggregate root classes |
| `services` | `tuple[ServiceType, ...]` | Tuple of registered service classes |
| `entities` | `tuple[EntityType, ...]` | Tuple of all discovered entities (non-root) from aggregate root field inspection |
| `value_objects` | `tuple[ValueObjectType, ...]` | Tuple of all discovered value objects from recursive field inspection |
| `name` | `str \| None` | Optional context name |

## Discovery Process

When constructed, `BoundedContext` recursively discovers all domain types referenced by the aggregate roots:

1. **Type extraction**: For each aggregate root, `typing.get_type_hints()` extracts all field types
2. **Recursive traversal**: For each discovered Entity or ValueObject type, its fields are also inspected
3. **Type categorisation**: Discovered types are split into entities and value objects and stored in `self.entities` and `self.value_objects`

```python
class ProductId(ValueObject):
    value: str

class OrderLine(Entity):
    product_id: ProductId
    quantity: int

class Order(RootEntity):
    id: str
    lines: list[OrderLine]

context = BoundedContext(aggregate_roots=[Order])
# Discovered: OrderLine (Entity), ProductId (ValueObject)
```

## Type Constraints Enforced

### Root Entity Nesting

No RootEntity can be nested inside another Entity:

```python
class User(RootEntity):
    id: str

class Order(RootEntity):
    id: str
    user: User  # InvalidNestedTypeError!
```

Instead, reference by ID:

```python
class Order(RootEntity):
    id: str
    user_id: str  # OK
```

### Value Object Constraints

ValueObjects can only contain primitives or other ValueObjects:

```python
class Order(Entity):
    id: str

class OrderLine(ValueObject):
    order: Order  # InvalidNestedTypeError! Entity not allowed in VO
```

### Service Method Constraints

Service methods cannot accept or return non-root Entity subclasses:

```python
class User(Entity):
    id: str

class UserService(Service):
    def get_user(self, user_id: str) -> User:  # InvalidServiceParameterError!
        pass
```

Allowed: `RootEntity`, `ValueObject`, custom classes, primitives.

### Duplicate Detection

`BoundedContext` itself does not detect duplicates globally. Duplicate detection happens at the `App` level when multiple contexts are composed:

```python
from aod.domain import App

context1 = BoundedContext(aggregate_roots=[User], name="users")
context2 = BoundedContext(aggregate_roots=[User], name="admin")

app = App("myapp", context1, context2)  # DuplicateDomainTypeError!
```

## `describe()` Method

```python
def describe(self) -> list[TypeDoc]: ...
```

Returns a list of `TypeDoc` objects describing every type in the context, categorised by role (`RootEntity`, `Entity`, `ValueObject`, `Service`). Each `TypeDoc` includes field names, types, and defaults.

| Parameter | Type | Description |
|-----------|------|-------------|
| (none) | — | — |

Returns `list[TypeDoc]` — documentation entries for all domain types in this context.

## `__repr__()` Method

Returns `self.name` if set, otherwise the default class representation.

## App Composition

`App` composes multiple `BoundedContext` instances and enforces global duplicate detection:

```python
from aod.domain import App

class Product(RootEntity):
    id: str

class Order(RootEntity):
    id: str

product_context = BoundedContext(aggregate_roots=[Product], name="products")
order_context = BoundedContext(aggregate_roots=[Order], name="orders")

app = App("ecommerce", product_context, order_context)
```

### `App.__init__()` Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Application name |
| `*contexts` | `BoundedContext` | One or more bounded contexts to compose |

Raises `DuplicateDomainTypeError` if any domain type appears in more than one context.

## Common Patterns

### E-Commerce

```python
class Product(RootEntity):
    id: str
    name: str
    price: float

class Order(RootEntity):
    id: str
    product_id: str
    quantity: int

product_context = BoundedContext(
    aggregate_roots=[Product],
    name="products",
)

order_context = BoundedContext(
    aggregate_roots=[Order],
    name="orders",
)
```

### User Management

```python
class User(RootEntity):
    id: str
    email: str
    name: str

class Role(ValueObject):
    name: str
    permissions: list[str]

class UserService(Service):
    def assign_role(self, user: User, role: str) -> None: ...

user_context = BoundedContext(
    aggregate_roots=[User],
    services=[UserService],
    name="users",
)
```

## Exceptions

| Exception | Raised When |
|-----------|-------------|
| `InvalidEntityTypeError` | An aggregate root is not a subclass of `Entity` |
| `InvalidRootEntityTypeError` | An aggregate root is an `Entity` but not a `RootEntity` |
| `InvalidServiceTypeError` | A service is not a subclass of `Service` |
| `ClassExpectedError` | A class is expected but an instance was provided |
| `InvalidNestedTypeError` | An Entity or ValueObject field references a RootEntity |
| `InvalidServiceParameterError` | A service method uses a non-root Entity as parameter/return type |
| `DuplicateDomainTypeError` | Same domain type registered in multiple contexts (raised by `App`) |

## Next Steps

- [Entity & RootEntity](entities.md) — Learn about aggregate roots
- [ValueObject](value-objects.md) — Learn about value objects
- [Service](services.md) — Learn about services
- [Event System](events.md) — Learn about domain events