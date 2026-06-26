# Invariants

Invariants enforce domain rules at construction time. The framework provides `@field_invariance` for field-level rules and `@invariance` for model-level rules. Violations raise `InvarianceException`.

## Imports

```python
from aod.domain.validation import (
    AfterValidator,
    BeforeValidator,
    field_invariance,
    invariance,
    mutable,
)
```

## AfterValidator

`AfterValidator` validates a value after type coercion (e.g., after strings are converted to numbers).

```python
from aod.domain.validation import AfterValidator


class Money(ValueObject):
    amount: float = AfterValidator(lambda v: v if v > 0 else (_ for _ in ()).throw(ValueError("amount must be positive")))
```

### Signature

```python
AfterValidator(func: Callable[[Any], Any])
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `func` | `Callable[[Any], Any]` | A callable that receives the validated value and must return the (possibly transformed) value, or raise an exception to reject it |

The function receives the value after Pydantic's built-in type coercion and validation. It runs only on normal `__init__`, not during `reconstruct()`.

## BeforeValidator

`BeforeValidator` validates a value before type coercion (e.g., trimming whitespace before string validation).

```python
from aod.domain.validation import BeforeValidator


class User(Entity):
    name: str = BeforeValidator(lambda v: v.strip() if isinstance(v, str) else v)
```

### Signature

```python
BeforeValidator(func: Callable[[Any], Any])
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `func` | `Callable[[Any], Any` | A callable that receives the raw value before type coercion and must return the (possibly transformed) value, or raise an exception to reject it |

Useful for normalising input (trimming whitespace, lowercasing, etc.) before type validation.

## field_invariance

`field_invariance` registers a field-level invariant. It converts `ValueError` and `AssertionError` raised by the decorated method into `InvarianceException`.

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
```

### Signature

```python
def field_invariance(
    *fields: str,
    mode: Literal["before", "after"] = "before",
    check_fields: bool = False,
    name: str | None = None,
) -> Callable: ...
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `*fields` | `str` | (required) | One or more field names this invariant validates |
| `mode` | `"before" \| "after"` | `"before"` | When to run the validator: `"before"` Pydantic's processing, or `"after"` |
| `check_fields` | `bool` | `False` | Whether to verify that the field names actually exist on the model |
| `name` | `str \| None` | `None` | Optional custom name for this invariant. Used in error messages and `check_invariant()` lookup. Defaults to the method name |

### The decorated method

The decorated method receives the field value and returns the (possibly transformed) value:

| Parameter | Type | Description |
|-----------|------|-------------|
| `cls` | `type` | The class being validated |
| `v` | `Any` | The field value to validate |

Should return the value (or a transformed version) or raise `ValueError` / `AssertionError` to reject.

Invariant violations become `InvarianceException` (a `DomainException`), not generic validation errors. The `reconstruct()` classmethod bypasses all invariants.

## invariance

`invariance` registers a model-level invariant. It receives the full model data as a dict and can validate relationships between fields. It converts `ValueError` and `AssertionError` into `InvarianceException`.

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

### Signature

```python
def invariance(
    fn: Callable | None = None,
    *,
    name: str | None = None,
) -> Callable: ...
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fn` | `Callable \| None` | `None` | The decorated function, or `None` if called with keyword arguments `@invariance(name="...")` |
| `name` | `str \| None` | `None` | Optional custom name for this invariant. Used in error messages and `check_invariant()` lookup. Defaults to the method name |

### The decorated method

The decorated method receives the model data dict and returns it (or raises).

```python
@invariance
def end_after_start(cls, data: dict) -> dict:
    if data["end"] <= data["start"]:
        raise ValueError("end must be after start")
    return data
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `cls` | `type` | The class being validated |
| `data` | `dict` | The model data as a dictionary with all fields populated |

Must return the model data dictionary (or any dict) or raise `ValueError` / `AssertionError`.

Same as `field_invariance`: violations raise `InvarianceException` and are bypassed by `reconstruct()`.

## @mutable

`@mutable` is a decorator that marks a method to inherit the mutation context of its caller, bypassing the `can_mutate()` guard on entities. This allows methods to mutate fields even when mutation would normally be blocked.

```python
from aod.domain.validation import mutable


class User(RootEntity):
    id: UserId
    _locked: bool = PrivateField(default=False)

    def can_mutate(self) -> bool:
        return not self._locked

    @mutable
    def unlock(self) -> None:
        self._locked = False
```

Without `@mutable`, `unlock()` would raise `MutationForbiddenException` because `can_mutate()` returns `False` when the entity is locked.

### Signature

```python
def mutable(fn: Callable) -> Callable: ...
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `fn` | `Callable` | The method to wrap with INHERIT mutation context |

This is also needed for methods called from `__post_init__` that need to mutate fields.

## Testing

### `check_invariant()`

```python
from aod.testing import check_invariant

check_invariant(Money, "amount_must_be_positive", amount=-10.0)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `cls` | `type` | The domain class that has the invariant |
| `invariant_name` | `str` | The name of the invariant (method name or the `name=` argument) |
| `data` | `dict[str, Any] \| None` | Optional dict of field values |
| `**kwargs` | `Any` | Additional field values as keyword arguments |

Raises `InvarianceException` if the invariant is violated. Raises `ValueError` if no invariant with that name is found on the class.

### `build()`

```python
from aod.testing import build

money = build(Money, amount=-10.0, currency="USD")
```

Skips all validation, including invariants. Use `check_invariant()` to manually test invariants on built objects.

## Common Patterns

### Required Field

```python
class User(Entity):
    id: str     # Required — must be provided
    name: str   # Required — must be provided
```

### Optional Field

```python
from typing import Optional


class User(Entity):
    id: str
    name: str
    email: Optional[str] = None
```

### Default Value

```python
class Config(ValueObject):
    host: str = "localhost"
    port: int = 8080
```

### Field Validation with field_invariance

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

### Model Validation with invariance

```python
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
| `InvarianceException(DomainException, ValueError)` | A `field_invariance` or `invariance` validator rejects the value |
| `ModelValidationError(DomainException)` | Validation fails during `__init__` |

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="entities.md">Entity & RootEntity</a></h3>
<p>Learn about entity validation</p>
</div>

<div class="feature-card">
<h3><a href="value-objects.md">ValueObject</a></h3>
<p>Learn about value object validation</p>
</div>

<div class="feature-card">
<h3><a href="../testing/index.md">Testing</a></h3>
<p>Learn about testing with invariants</p>
</div>

</div>