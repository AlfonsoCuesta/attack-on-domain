# Validation Decorators

## Purpose

DDD-aligned decorators for declaring field-level and model-level invariants that become Pydantic validators.

## ValidatorInfo

A metadata holder that stores validator configuration (`args`, `kwargs`, `validation` callable). When called with a function, it applies the validation decorator to that function:

```python
ValidatorInfo(validation=pydantic_field_validator, "age", mode="before")(fn)
# → pydantic_field_validator("age", mode="before")(fn)
```

## Decorators

### `@field_invariance(*fields, mode="before", check_fields=False)`
Decorator factory. Marks a classmethod as a Pydantic `field_validator`.
- Stores `ValidatorInfo` in the function's `__field_validator_info__` attribute
- Wraps in `classmethod` if not already one
- Detected by `is_validator()` in `model_maker.py` → injected into validation model only

```python
@field_invariance("age")
def normalize_age(cls, value: int) -> int:
    return value + 10
```

### `@invariance`
Decorator. Marks a method as a Pydantic `model_validator(mode="after")`.
- Wraps the function so it auto-returns `self` after calling the original
- Stores `ValidatorInfo` in `__field_validator_info__`
- Detected by `is_validator()` → injected into validation model only

```python
@invariance
def check_consistency(self) -> None:
    if self.age < 0:
        raise ValueError("Age cannot be negative")
```

**Do NOT return self** — the wrapper does it automatically.

## Introspection

### `is_validator(fn) -> ValidatorInfo | None`
Checks a function for `__field_validator_info__` attribute. Handles `classmethod` wrapping (checks `fn.__func__` if the direct attribute is not found).

## How model_maker Uses These

```python
for k, v in cls.__dict__.copy().items():
    if validator_info := is_validator(v):
        full_ns[k] = validator_info(v)
        # validator_info(v) applies pydantic's decorator to the function
        # e.g., pydantic_model_validator(mode="after")(v)
```
