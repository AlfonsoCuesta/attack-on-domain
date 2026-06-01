# attack-on-domain — Agent Guide

## Overview

`attack-on-domain` is a Python 3.14+ library providing Domain-Driven Design building blocks using Pydantic v2 under the hood. It implements entities, value objects, bounded contexts, domain events, and a dual-model validation system.

**Source code is under `code/`** — this directory is mapped as the package root in `pyproject.toml`.

## Project Structure

```
code/
├── aod/                          # Public package
│   ├── __init__.py               # Re-exports: BoundedContext, DomainEvent, Entity, RootEntity, ValueObject, Service, Field, PrivateField
│   ├── py.typed                  # PEP 561 marker
│   ├── exceptions/__init__.py    # Public: DomainException, MutationForbiddenException
│   ├── validation/__init__.py    # Public: AfterValidator, BeforeValidator, field_invariance, invariance, super_context
│   ├── diagram.py                # Interactive DDD diagram generator
│   └── _internal/                # Private — not semver-stable
│       ├── core/                 # Framework internals
│       │   ├── base_validator.py     # ValidationModelMeta + BaseValidator
│       │   ├── base_sealed.py        # BaseSealed (always-blocked mutation)
│       │   ├── base_guarded/         # BaseGuarded, MutatingContext, make_immutable subsystem
│       │   ├── event_emitter.py      # Event, EventEmitter, EventCollector
│       │   ├── model_maker.py        # Dual Pydantic model generation
│       │   ├── domain_exception.py   # DomainException hierarchy
│       │   ├── type_checking/        # DDD type constraint extractors
│       │   │   ├── __init__.py       # Re-exports: extract_types_from_annotation, extract_domain_types_from_model
│       │   │   └── extractors.py     # extract_types_from_annotation, get_validation_model
│       │   ├── type_handlers/        # DDD type check functions
│       │   │   ├── __init__.py       # Re-exports: BaseGuardedTypeHandler, ServiceTypeHandler
│       │   │   ├── base_guarded_handler.py  # check_entity, check_root_entity, check_value_object, discover_types
│       │   │   └── service_handler.py       # check_service
│       │   ├── fields/fields.py      # Field(), PrivateField() wrappers
│       │   └── invariances/invariances.py  # field_invariance, invariance, is_validator
│       └── domain/               # DDD domain primitives
│           ├── value_object.py
│           ├── entity.py
│           ├── service.py
│           ├── app.py
│           ├── bounded_context.py
│           ├── describe.py
│           └── describers/
│               ├── __init__.py
│               ├── base_guarded_describer.py
│               └── service_describer.py
└── tests/                        # All tests
    ├── test_public_api.py
    ├── core/                     # Core framework tests
    │   ├── test_base_guarded.py
    │   ├── test_mutating_context.py
    │   ├── test_post_init.py
    │   ├── make_immutable/
    │   └── type_checking/
    └── domain/                   # Domain class tests
        ├── test_app.py
        ├── test_bounded_context.py
        ├── test_describe.py
        ├── test_entity.py
        ├── test_event_emitter.py
        ├── test_service.py
        └── test_value_object.py
```

## Key Architectural Decisions

### Single Metaclass: `ValidationModelMeta`
Only one metaclass exists in the framework — `ValidationModelMeta` on `BaseValidator`. It generates the two Pydantic models (`__validation_model__` and `__raw_model__`) at class creation time.

The old `GuardedBaseMeta` and `EntityMeta` metaclasses were eliminated:
- **Method wrapping** lives in `BaseGuarded.__init_subclass__` which calls `_wrap_public_methods(cls)`
- **Root entity flag** uses `issubclass(cls, RootEntity)` — no flag variable needed
- `ValidationModelMeta.__new__` accepts `**kwargs` and forwards them to `type.__new__` for `__init_subclass__` compatibility

### Dual-Model Validation
Each user class gets two Pydantic models at class creation time:
- **Validation model** (`__validation_model__`): includes all field constraints, `@field_invariance` validators, and `@invariance` model validators
- **Raw model** (`__raw_model__`): strips all validators from annotations, excludes `@field_invariance` and `@invariance`

`__init__` uses the validation model by default. `from_existing()` (classmethod) uses the raw model, allowing reconstruction without re-validation.

### ContextVar Model Selection
`BaseValidator.__init__` checks a `contextvars.ContextVar` (`_use_raw_model`) to decide which model to validate against. `from_existing()` sets this flag before calling `cls(**kwargs)`.

### EventEmitter via PrivateField
All domain classes (`Entity`, `ValueObject`, `Service`) declare `_event_emitter` as a `PrivateField(default_factory=EventEmitter)` instead of creating it manually in `__init__`. Pydantic handles the lifecycle automatically.

### Automatic Method Wrapping via `__init_subclass__`
`BaseGuarded.__init_subclass__` calls `_wrap_public_methods(cls)` when any subclass is created. This wraps all public non-dunder instance methods with a mutation context manager. It skips:
- Dunder methods (`__*__`)
- Methods already marked with `__mutable__` attribute
- Methods decorated with `@field_invariance` or `@invariance` (they have `__field_validator_info__`)

### Immutable Proxies via `make_immutable`
When an attribute is read outside a mutation context, `BaseGuarded.__getattribute__` returns `make_immutable(value)`:
- `list` → `ImmutableList` (blocks append, extend, __setitem__, etc.)
- `dict` → `ImmutableDict` (blocks __setitem__, update, pop, etc.)
- `set` → `ImmutableSet` (blocks add, remove, discard, etc.)
- Custom objects → dynamically created `Immutable{ClassName}` subclass (wraps getattr, blocks setattr/delattr/mutating dunders)

### Event Collection via ContextVar
`EventEmitter.emit()` always appends to its local list. If a `EventCollector` context manager is active (via ContextVar), it also appends to the collector's list. This enables aggregate-level event collection without explicit child traversal.

### `__post_init__` Hook

Defined on `BaseValidator` (empty) and triggered from `BaseGuarded.__init__`. Only runs on normal `__init__`, **not** on `from_existing`. It executes after `__mutating_context__` exists but before `__initialized__ = True`, so:
- Public methods can be called (mutation context active)
- `_event_emitter` is already available (assigned by Pydantic via PrivateField before `__post_init__` runs)
- Field mutation is allowed during the hook

```python
class User(RootEntity):
    id: int
    name: str

    def __post_init__(self):
        self._event_emitter.emit(UserCreatedEvent(user_id=self.id))
        self.setup_defaults()

    def setup_defaults(self):
        # public method — works because __mutating_context__ exists
        ...
```

Works for `Entity`, `RootEntity`, `ValueObject`, `Service` (all inherit from `BaseGuarded`). Direct `BaseValidator` subclasses define the method but don't trigger it.

### Type Checking System (`type_handlers/`)
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
- Checks root entity status via `issubclass(item, RootEntity)` — no `is_root()` classmethod needed
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
uv run pytest code/tests -q        # Run tests (199 tests)
uv run ruff check code/ && uv run ruff format --check code/  # Lint + format check
ty check                          # Type check
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
- If you change the mutation system, update `base_guarded.py` and verify `test_base_guarded.py` + `test_make_immutable.py`
- If you change `__post_init__`, update `base_validator.py` (definition), `base_guarded.py` (trigger), and verify `test_post_init.py`
- If you change domain classes, check `test_event_emitter.py`, `test_entity.py`, `test_value_object.py`
- If you change type checks, update `type_handlers/extractors.py` and/or `type_handlers/checks` and verify tests
- If you change bounded context logic, update `bounded_context.py` and check `test_bounded_context.py`
- Always run all tests before committing
- `Event.emitted_at` is the timestamp field.

## Dependencies

- **Runtime**: `pydantic>=2.12.4`, `typing-inspect>=0.9.0`
- **Dev**: `ruff`, `ty`, `pre-commit`, `pytest`
- **Build**: `setuptools`, `wheel`
