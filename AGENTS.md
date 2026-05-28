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
│       │   ├── type_checking/        # DDD type constraints
│       │   │   ├── __init__.py       # Re-exports: extract_types_from_annotation, check_entity, check_root_entity, check_value_object, check_service
│       │   │   ├── extractors.py     # extract_types_from_annotation, get_validation_model
│       │   │   └── checks.py         # check_entity, check_root_entity, check_value_object, check_service
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
    │   └── type_checking/
    │       ├── test_extractors.py
    │       └── test_checks.py
    └── domain/                   # Domain class tests
        ├── test_bounded_context.py
        ├── test_entity.py
        ├── test_service.py
        └── test_value_object.py
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

### Type Checking System (`type_checking/`)
Three check functions enforce DDD type constraints at `BoundedContext` construction:

#### `check_entity(entity_cls)` / `check_root_entity(entity_cls)`
Raises `InvalidNestedTypeError` if any field references `RootEntity` (or any subclass of it).

#### `check_value_object(vo_cls)`
Raises `InvalidNestedTypeError` if any field references `Entity` **or** `RootEntity` (ValueObjects must only contain primitives or other ValueObjects).

#### `check_service(service_cls)`
Iterates all public methods via `inspect.getmembers`. For each method:
- Inspects parameters and return type via `inspect.signature`
- Resolves forward references via `typing.get_type_hints`
- Raises `InvalidServiceParameterError` if any param or return type is a non-root `Entity`

**Allowed in services**: custom classes, `RootEntity`, `ValueObject`
**Forbidden in services**: non-root `Entity`

### BoundedContext Constructor
```python
class BoundedContext:
    def __init__(
        self,
        aggregate_roots: Optional[Iterable[RootEntityType]] = None,
        services: Optional[Iterable[ServiceType]] = None,
    ):
```
- Only accepts `aggregate_roots` (RootEntity subclasses) and `services` (Service subclasses)
- Discovers `entities` and `value_objects` recursively via `_discover_types()`:
  - Starts from each root entity, gets `typing.get_type_hints()`
  - For each field type, extracts all types via `extract_types_from_annotation()`
  - Recursively traverses discovered Entity and ValueObject fields
- Runs check functions on all discovered types

### Public exceptions in `aod.exceptions`
Only two exported exceptions:
- `DomainException` — base for all domain errors
- `MutationForbiddenException` — raised when mutating an immutable object

Other exceptions (`InvalidNestedTypeError`, `InvalidServiceParameterError`, `ClassExpectedError`, etc.) remain in `_internal` and are not part of the public API.

## Development Commands

```bash
uv run pytest code/tests -q        # Run tests (160 tests)
uv run black code/ --target-version py314 --check  # Format check
uv run mypy code/                  # Type check
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
- If you change type checks, update `type_checking/extractors.py` and/or `type_checking/checks.py` and check `test_extractors.py` + `test_checks.py`
- If you change bounded context logic, update `bounded_context.py` and check `test_bounded_context.py`
- Always run all tests before committing
- The `Event` class has a typo: `emmited_at` instead of `emitted_at`. Do NOT fix it — it's a known established API.

## Dependencies

- **Runtime**: `pydantic>=2.12.4`, `typing-inspect>=0.9.0`
- **Dev**: `black`, `mypy`, `pre-commit`, `pytest`, `twine`
- **Build**: `setuptools`, `wheel`
