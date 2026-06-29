# Identity Field

Every `Entity` and `RootEntity` subclass must have exactly one identity field marked with `Field(id=True)`. The identity field can be any type — `int`, `str`, `UUID`, or a custom type — and the framework enforces the "exactly one" rule at class creation time.

## Marking the Identity Field

Use `Field(id=True)` to mark the identity field:

```python
from aod.domain import RootEntity, Field


class User(RootEntity):
    id: int = Field(id=True)
    name: str
    email: str
```

Any type works as an identity field:

```python
import uuid
from aod.domain import Entity, Field


class Order(Entity):
    id: uuid.UUID = Field(id=True)
    total: float


class Post(Entity):
    id: str = Field(id=True)
    title: str
```

## ValueObject as Identity

Identity fields can also be `ValueObject` subclasses, providing type safety and encapsulation:

```python
from aod.domain import RootEntity, ValueObject, Field


class UserId(ValueObject):
    value: str


class User(RootEntity):
    id: UserId = Field(id=True)
    name: str
    email: str

user = User(id=UserId(value="abc-123"), name="Alice", email="alice@example.com")
assert user.id.value == "abc-123"
```

ValueObject identities are compared by value — two entities with `UserId(value="abc-123")` are equal regardless of other fields. This is the recommended pattern for rich identity types that carry domain meaning.

## Distinguishing Identity from References

When an entity has multiple fields of the same type, `Field(id=True)` tells the framework which one is the identity:

```python
from aod.domain import RootEntity, Field


class User(RootEntity):
    id: int = Field(id=True)  # This is the identity
    manager_id: int           # This is a reference, not the identity
    name: str
```

## Exactly One Identity Field

The framework requires exactly one field marked with `Field(id=True)`:

```python
class User(RootEntity):
    id: int = Field(id=True)  # OK
    name: str


class BadEntity(Entity):
    name: str  # NoIdentityFieldException at class creation


class BadEntity2(Entity):
    id: int = Field(id=True)
    alt_id: int = Field(id=True)  # TooManyIdentityFieldsException
```

This check runs at class creation time — not at instantiation — so the error surfaces as soon as the class is defined.

## Mutating the ID Changes the Hash

You can change an entity's identity inside a method:

```python
class User(RootEntity):
    id: int = Field(id=True)
    name: str

    def reassign(self, new_id: int) -> None:
        self.id = new_id
```

However, changing the identity also changes the entity's hash. If the entity is stored in a `set` or used as a `dict` key, the hash change can cause subtle bugs:

```python
user = User(id=1, name="Alice")
s = {user}
d = {user: "found"}

user.reassign(2)

assert user in s  # False! Hash changed after insertion
assert user in d  # False! Hash changed after insertion
```

**Best practice:** avoid mutating an entity's identity after construction. If you need to change the identity, create a new entity or ensure the entity was never placed in a set/dict before the mutation.

## Equality by Identity

Entities compare by their identity field value, not by their other fields:

```python
class User(RootEntity):
    id: int = Field(id=True)
    name: str

u1 = User(id=1, name="Alice")
u2 = User(id=1, name="Bob")
assert u1 == u2  # True — same identity
assert hash(u1) == hash(u2)
```

Different entity types with the same identity value are never equal:

```python
class Admin(RootEntity):
    id: int = Field(id=True)
    role: str

a = Admin(id=1, role="super")
u = User(id=1, name="x")
assert a != u  # Different types
```

## Exceptions

| Exception | Raised When |
|-----------|-------------|
| `NoIdentityFieldException` | An `Entity` or `RootEntity` subclass has no field marked with `Field(id=True)` |
| `TooManyIdentityFieldsException` | An `Entity` or `RootEntity` subclass has more than one field marked with `Field(id=True)` |

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="entities.md">Entity & RootEntity</a></h3>
<p>Learn about mutable domain objects with identity</p>
</div>

<div class="feature-card">
<h3><a href="value-objects.md">ValueObject</a></h3>
<p>Learn about immutable domain objects</p>
</div>

<div class="feature-card">
<h3><a href="validation.md">Invariants vs __post_init__</a></h3>
<p>Learn when to use invariants and when to use __post_init__</p>
</div>

</div>
