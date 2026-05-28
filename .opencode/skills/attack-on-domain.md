---
name: attack-on-domain
description: "Domain-Driven Design building blocks library: entities, value objects, bounded contexts, domain events, and Pydantic v2 validation."
---

# attack-on-domain — DDD Building Blocks

Library for Domain-Driven Design in Python 3.14+, built on Pydantic v2.

## Architecture

```
BaseValidator (PydanticFacadeMeta)
  └── BaseMutable (MutableBaseMeta)
        └── BaseImmutable

ValueObject → BaseImmutable
Entity      → BaseMutable (metaclass=EntityMeta)
RootEntity  → Entity(root=True)
Service     → plain class (not a validator)
```

## Key Concepts

### Dual-Model Architecture
Each user class gets **two** Pydantic models auto-generated at class creation:
- `__validation_model__` — includes all validators, constraints, Annotated metadata
- `__raw_model__` — strips all validators (only keeps base types + private fields)

`__init__` uses the validation model by default. `from_existing()` uses the raw model (bypasses field validators and `@invariance`).

### Validation Decorators (from `aod.validation`)
- `@field_invariance("field_name")` — Pydantic `field_validator`, runs only in validation model
- `@invariance` — Pydantic `model_validator(mode="after")`, runs only in validation model. **Do NOT return self**, the wrapper does it automatically.

Both are detected by `is_validator()` in `model_maker.py` and injected into the validation model.

### Mutation System
`BaseMutable` auto-wraps all public non-dunder methods with a mutation context manager. `__setattr__` and `__getattribute__` enforce mutation rules:
- `BLOCK` — no mutation allowed (default after init)
- `PASS` — temporary mutation allowed (entered by public method wrappers)
- `SUPER` — bypasses `_can_mutate()` (entered by `@super_context`)

When mutation is blocked, `__getattribute__` returns `make_immutable(value)` — wrapping lists/dicts/sets/custom objects in immutable proxies.

### Event System
- `Event(BaseImmutable)` — immutable event with auto-set `emmited_at`
- `EventEmitter` — per-object event registry. `emit()` stores locally + pushes to active `EventCollector` via `ContextVar`.
- `EventCollector` — context manager: `with EventCollector() as events:` captures all emitted events.

Every domain object has `self._event_emitter`. Use `self._event_emitter.emit(event)` instead of `self._emit(event)`.

## Public API (`aod`)
`BoundedContext`, `DomainEvent`, `Entity`, `RootEntity`, `ValueObject`, `Field`, `PrivateField`

## Public API (`aod.validation`)
`AfterValidator`, `BeforeValidator`, `field_invariance`, `invariance`, `super_context`

## Conventions
- Python 3.14+, keyword-only args, no comments in code
- Tests use `uv run pytest code/tests`
- Format with `uv run black code/`, typecheck with `uv run mypy code/`
- Public API is only what's in `__all__` — never import from `_internal` in user code
