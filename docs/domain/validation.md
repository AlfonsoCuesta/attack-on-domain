# Validation

`attack-on-domain` provides validation tools built on top of Pydantic v2, with additional decorators for field invariants, model invariants, and mutation context management.

## Imports

```python
from aod.domain.validation import (
    AfterValidator,
    BeforeValidator,
    field_invariance,
    invariance,
    inherit_context,
)
```

## AfterValidator

`AfterValidator` is re-exported from Pydantic's `pydantic.AfterValidator`. It validates a value after Pydantic has processed it (e.g., after type coercion).

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

`BeforeValidator` is re-exported from Pydantic's `pydantic.BeforeValidator`. It validates a value before Pydantic processes it (e.g., before type coercion).

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

`field_invariance` is a decorator that registers a classmethod as a field-level invariant. It wraps Pydantic's `field_validator` and converts `ValueError` / `AssertionError` into `InvarianceException`.

```python
from aod.domain.validation import field_invariance


class Money(ValueObject):
    amount: float
    currency: str

    @field_invariance("amount")
    @classmethod
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

The decorated method must be a `@classmethod` that receives the field value and returns the (possibly transformed) value:

| Parameter | Type | Description |
|-----------|------|-------------|
| `cls` | `type` | The class being validated |
| `v` | `Any` | The field value to validate |

Should return the value (or a transformed version) or raise `ValueError` / `AssertionError` to reject.

### Difference from Pydantic validators

`field_invariance` wraps Pydantic's `field_validator` but catches `ValueError` and `AssertionError` and re-raises them as `InvarianceException(DomainException, ValueError)`. This means:

- Invariant violations are domain exceptions, not generic validation errors
- `ModelValidationError` wraps Pydantic's `ValidationError` but if the cause is an `InvarianceException`, it is re-raised directly
- `reconstruct()` bypasses all validators including `field_invariance`

## invariance

`invariance` is a decorator that registers a classmethod as a model-level invariant. It wraps Pydantic's `model_validator(mode="after")` and converts `ValueError` / `AssertionError` into `InvarianceException`.

```python
from datetime import datetime

from aod.domain.validation import invariance


class DateRange(ValueObject):
    start: datetime
    end: datetime

    @invariance
    @classmethod
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

The decorated method must be a `@classmethod` that receives the model instance and returns it (or raises).

```python
@invariance
@classmethod
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

### Difference from Pydantic model_validator

Same as `field_invariance`: catches `ValueError`/`AssertionError` and re-raises as `InvarianceException`. Bypassed by `reconstruct()`.

## inherit_context

`inherit_context` is a decorator that marks a method to inherit the mutation context of its caller. This allows methods to mutate fields even when called from outside the normal method-guarded path (e.g., called from another method or from `__post_init__`).

```python
from aod.domain.validation import inherit_context


class User(Entity):
    id: str
    name: str

    @inherit_context
    def internal_method(self) -> None:
        self.name = "new name"
```

### Signature

```python
def inherit_context(fn: Callable) -> Callable: ...
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `fn` | `Callable` | The method to wrap with INHERIT mutation context |

The decorated method will use `MutatingState.INHERIT` instead of `MutatingState.PASS`, meaning it propagates the caller's mutation permission rather than setting its own PASS state. This is needed for:

- Methods called from `__post_init__` that need to mutate fields
- Methods called from outside as part of a batch operation
- The internal `_can_mutate()` method on `BaseGuarded`

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
    @classmethod
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
    @classmethod
    def end_after_start(cls, data: dict) -> dict:
        if data["end"] <= data["start"]:
            raise ValueError("end must be after start")
        return data
```

## Exceptions

| Exception | Raised When |
|-----------|-------------|
| `InvarianceException(DomainException, ValueError)` | A `field_invariance` or `invariance` validator rejects the value |
| `ModelValidationError(DomainException)` | Pydantic validation fails during `__init__` (wraps `ValidationError`) |

## Next Steps

- [Entity & RootEntity](entities.md) — Learn about entity validation
- [ValueObject](value-objects.md) — Learn about value object validation
- [Testing](../testing/index.md) — Learn about testing with invariants