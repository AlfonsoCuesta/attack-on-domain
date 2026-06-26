# EntityId

`EntityId` is a specialized `ValueObject` that represents the identity of an `Entity`. Every entity must have exactly one field of type `EntityId` — the framework enforces this at class creation time.

Because `EntityId` inherits from `ValueObject`, identities are immutable and compared by their internal value. Two entities with the same `EntityId` are considered the same entity.

## Simple Identity

A single-field identity using a `value` field is the most common form:

```python
from aod.domain import EntityId


class UserId(EntityId):
    value: str


class OrderId(EntityId):
    value: int
```

## Composite Identity

An `EntityId` can have multiple fields, forming a composite key:

```python
class UserId(EntityId):
    email: str
    phone: str
```

Two identities are equal only when all fields match:

```python
a = UserId(email="alice@example.com", phone="+1-555-0100")
b = UserId(email="alice@example.com", phone="+1-555-0100")
assert a == b  # True

c = UserId(email="alice@example.com", phone="+1-555-0101")
assert a != c  # Different phone
```

## Key Characteristics

### Immutable

`EntityId` is a `ValueObject`, so it cannot be changed after creation:

```python
uid = UserId(value="abc")
uid.value = "def"  # MutationForbiddenException!
```

### Compared by Value

Two `EntityId` instances with the same field values are equal:

```python
a = UserId(value="abc")
b = UserId(value="abc")
assert a == b  # True
```

### Structural Equality for Entities

Entities use their `EntityId` for equality and hashing. Two entities with the same `EntityId` are equal:

```python
class User(RootEntity):
    id: UserId
    name: str

uid = UserId(value="abc")
u1 = User(id=uid, name="Alice")
u2 = User(id=uid, name="Bob")
assert u1 == u2  # True — same identity
assert hash(u1) == hash(u2)
```

Different entity types with the same identity value are never equal:

```python
class Admin(RootEntity):
    id: UserId
    role: str

a = Admin(id=UserId(value="1"), role="super")
u = User(id=UserId(value="1"), name="x")
assert a != u  # Different types
```

## Each Entity Needs Exactly One EntityId

The framework requires every `Entity` and `RootEntity` subclass to have exactly one field typed as an `EntityId` subclass:

```python
class User(RootEntity):
    id: UserId       # One EntityId field — OK
    name: str

class BadEntity(Entity):
    name: str        # No EntityId — NoEntityIdException at class creation

class BadEntity2(Entity):
    id1: UserId
    id2: OrderId     # Two EntityId fields — TooManyEntityIdsException
```

This check runs at class creation time — not at instantiation — so the error surfaces as soon as the class is defined.

## Mutating the ID Changes the Hash

You can change an entity's identity inside a method:

```python
class User(RootEntity):
    id: UserId
    name: str

    def reassign(self, new_id: UserId) -> None:
        self.id = new_id
```

However, changing the identity also changes the entity's hash. If the entity is stored in a `set` or used as a `dict` key, the hash change can cause subtle bugs:

```python
uid1 = UserId(value="a")
uid2 = UserId(value="b")

user = User(id=uid1, name="Alice")
s = {user}
d = {user: "found"}

user.reassign(uid2)

assert user in s      # False! Hash changed after insertion
assert user in d      # False! Hash changed after insertion
```

**Best practice:** avoid mutating an entity's identity after construction. If you need to change the identity, create a new entity or ensure the entity was never placed in a set/dict before the mutation.

## The `evolve()` Method

`EntityId` provides an `evolve()` method that creates a new identity with some fields changed, while linking to the previous identity for change tracking:

```python
class UserId(EntityId):
    value: str
    tenant: str = "default"

uid = UserId(value="abc")
uid2 = uid.evolve(tenant="acme")

assert uid2.value == "abc"
assert uid2.tenant == "acme"
assert uid2.last_id is uid  # Links to the original
```

The `last_id` public property is readable by persistence layers to trace identity chains and find the previous row for updates.

This is useful for persistence layers that need to track identity changes.

### `evolve()` Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `**changes` | `Any` | Fields to override in the new identity |

Returns a new `EntityId` instance with the requested changes. Fields not present in `changes` keep their current values.

## Testing

```python
from aod.testing import build

user = build(User, id=UserId(value="abc"), name="Alice")
```

## Exceptions

| Exception | Raised When |
|-----------|-------------|
| `NoEntityIdException` | An `Entity` or `RootEntity` subclass has no `EntityId` field |
| `TooManyEntityIdsException` | An `Entity` or `RootEntity` subclass has more than one `EntityId` field |

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="entities.md">Entity & RootEntity</a></h3>
<p>Learn about mutable domain objects with EntityId identity</p>
</div>

<div class="feature-card">
<h3><a href="value-objects.md">ValueObject</a></h3>
<p>Learn about immutable domain objects — EntityId is a specialized ValueObject</p>
</div>

<div class="feature-card">
<h3><a href="validation.md">Invariants vs __post_init__</a></h3>
<p>Learn when to use invariants and when to use __post_init__</p>
</div>

</div>
