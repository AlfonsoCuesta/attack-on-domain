# attack-on-domain — Agent Guide

## Overview

`attack-on-domain` is a Python 3.14+ library providing Domain-Driven Design building blocks using Pydantic v2 under the hood. It implements entities, value objects, bounded contexts, domain events, and a dual-model validation system.

**Source code is under `code/`** — this directory is mapped as the package root in `pyproject.toml`.

## Project Structure

```
code/
├── aod/                          # Public package
│   ├── __init__.py               # Re-exports: BoundedContext, DomainEvent, Entity, RootEntity, ValueObject, Field, PrivateField
│   ├── py.typed                  # PEP 561 marker
│   ├── exceptions/__init__.py    # Public: DomainException, MutationForbiddenException
│   ├── validation/__init__.py    # Public: AfterValidator, BeforeValidator, field_invariance, invariance, super_context
│   └── _internal/                # Private — not semver-stable
│       ├── core/                 # Framework internals
│       │   ├── base_validator.py     # PydanticFacadeMeta + BaseValidator
│       │   ├── base_immutable.py     # BaseImmutable (always-blocked mutation)
│       │   ├── base_mutable/         # BaseMutable, MutableBaseMeta, MutatingContext, make_immutable subsystem
│       │   ├── event_emitter.py      # Event, EventEmitter, EventCollector
│       │   ├── model_maker.py        # Dual Pydantic model generation
│       │   ├── domain_exception.py   # DomainException hierarchy
│       │   ├── fields/fields.py      # Field(), PrivateField() wrappers
│       │   └── invariances/invariances.py  # field_invariance, invariance, is_validator
│       └── domain/               # DDD domain primitives
│           ├── value_object.py
│           ├── entity.py
│           ├── service.py
│           └── bounded_context.py
└── tests/                        # All tests
    ├── test_public_api.py
    ├── core/                     # Core framework tests
    └── domain/                   # Domain class tests
```

## Key Architectural Decisions

### Dual-Model Validation
Each user class gets two Pydantic models at class creation time:
- **Validation model** (`__validation_model__`): includes all field constraints, `@field_invariance` validators, and `@invariance` model validators
- **Raw model** (`__raw_model__`): strips all validators from annotations, excludes `@field_invariance` and `@invariance`

`__init__` uses the validation model by default. `from_existing()` (classmethod) uses the raw model, allowing reconstruction without re-validation.

### ContextVar Model Selection
`BaseValidator.__init__` checks a `contextvars.ContextVar` (`_use_raw_model`) to decide which model to validate against. `from_existing()` sets this flag before calling `cls(**kwargs)`.

### Automatic Method Wrapping
`MutableBaseMeta` (the metaclass) intercepts class creation and wraps all public non-dunder instance methods with a mutation context manager. This is what makes setters and mutating methods work transparently. It skips:
- Dunder methods (`__*__`)
- Methods already marked with `__mutable__` attribute
- Methods decorated with `@field_invariance` or `@invariance` (they have `__field_validator_info__`)

### Immutable Proxies via `make_immutable`
When an attribute is read outside a mutation context, `BaseMutable.__getattribute__` returns `make_immutable(value)`:
- `list` → `ImmutableList` (blocks append, extend, __setitem__, etc.)
- `dict` → `ImmutableDict` (blocks __setitem__, update, pop, etc.)
- `set` → `ImmutableSet` (blocks add, remove, discard, etc.)
- Custom objects → dynamically created `Immutable{ClassName}` subclass (wraps getattr, blocks setattr/delattr/mutating dunders)

### Event Collection via ContextVar
`EventEmitter.emit()` always appends to its local list. If a `EventCollector` context manager is active (via ContextVar), it also appends to the collector's list. This enables aggregate-level event collection without explicit child traversal.

## Development Commands

```bash
uv run pytest code/tests -q        # Run tests (117 tests)
uv run pytest code/tests -v        # Verbose
uv run black code/                  # Format
uv run mypy code/                   # Type check
```

## Coding Conventions

1. **Python 3.14+** — use `|` for unions, `type[X]`, `Self`, etc.
2. **Keyword-only arguments** everywhere
3. **No comments** in source code — code should be self-documenting
4. **No emojis** unless explicitly requested by the user
5. Tests mirror source structure under `code/tests/`
6. Never import from `_internal` in user-facing code — only through `aod`, `aod.validation`, `aod.exceptions`

## When Modifying This Code

- If you change the dual-model system, update `model_maker.py` and verify `test_base_validator.py`
- If you change the mutation system, update `base_mutable.py` and verify `test_base_mutable.py` + `test_make_immutable.py`
- If you change domain classes, check `test_event_emitter.py`, `test_entity.py`, `test_value_object.py`
- Always run all tests before committing
- The `Event` class has a typo: `emmited_at` instead of `emitted_at`. Do NOT fix it — it's a known established API.

## Dependencies

- **Runtime**: `pydantic>=2.12.4`, `typing-inspect>=0.9.0`
- **Dev**: `black`, `mypy`, `pre-commit`, `pytest`, `twine`
- **Build**: `setuptools`, `wheel`
