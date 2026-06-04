# attack-on-domain — Agent Guide

## Overview

`attack-on-domain` is a Python 3.14+ library providing Domain-Driven Design building blocks using Pydantic v2 under the hood. It implements entities, value objects, bounded contexts, domain events, and a dual-model validation system.

**Source code is under `code/`** — this directory is mapped as the package root in `pyproject.toml`.

## Project Structure

```
code/
├── aod/                              # Package root
│   ├── __init__.py                   # Empty package marker
│   ├── py.typed                      # PEP 561 marker
│   ├── domain/                       # Public domain layer (re-exports from _internal)
│   │   ├── __init__.py               # Re-exports: App, BoundedContext, DomainEvent, EventCollector, Entity, RootEntity, Service, ValueObject, Field, PrivateField
│   │   └── validation/               # Public: AfterValidator, BeforeValidator, field_invariance, invariance, inherit_context
│   ├── exceptions/__init__.py        # Public: DomainException, MutationForbiddenException
│   ├── diagram.py                    # Interactive DDD diagram generator
│   └── _internal/                    # Private — not semver-stable
│       ├── core/                     # Framework internals
│       │   ├── base_validator.py     # ValidationModelMeta + BaseValidator
│       │   ├── reconstructable.py    # ReconstructMixin (reconstruct classmethod)
│       │   ├── base_sealed.py        # BaseSealed (always-blocked mutation)
│       │   ├── base_guarded/         # BaseGuarded, MutatingContext, make_immutable subsystem
│       │   ├── event_emitter.py      # Event, EventEmitter, EventCollector
│       │   ├── model_maker.py        # Dual Pydantic model generation
│       │   ├── domain_exception.py   # DomainException hierarchy
│       │   ├── type_checking/        # DDD type constraint extractors
│       │   │   ├── __init__.py       # Re-exports: extract_types_from_annotation
│       │   │   └── extractors.py     # extract_types_from_annotation
│       │   ├── type_handlers/        # DDD type check functions
│       │   │   ├── __init__.py       # Re-exports: BaseGuardedTypeHandler, ServiceTypeHandler
│       │   │   ├── base_guarded_handler.py  # check_entity, check_root_entity, check_value_object, discover_types
│       │   │   ├── generic_utils.py         # get_generic_arg_from_orig_bases, get_generic_arg_from_mro, validate_generic_arg_is_subclass
│       │   │   └── service_handler.py       # check_service
│       │   ├── fields/fields.py      # Field(), PrivateField() wrappers
│       │   └── invariances/invariances.py  # field_invariance, invariance, is_validator
│       ├── type_checks/             # Contract & handler validation
│       │   ├── __init__.py
│       │   ├── contract_checks.py   # validate_fields_no_entity, validate_result_contains_root_entity, extract_root_entity
│       │   ├── handler_checks.py    # extract_handler_type, validate_handler_type, validate_handler_entity, handler_type_entity
│       │   └── handler_checks_async.py  # Async mirror (same function signatures)
│       └── domain/                   # DDD domain primitives (implementation)
│           ├── value_object.py
│           ├── entity.py
│           ├── service.py
│           ├── app.py
│           ├── bounded_context.py
│           └── describe.py
│       ├── application/              # Application layer (packages)
│       │   ├── port.py               # Port base class (abstract, mutable-from-inside)
│       │   ├── repository/           # Command, Query, Repository (Protocol) — sync + async
│       │   │   ├── __init__.py       # Command, Query, Repository (sync Protocol)
│       │   │   └── async_.py         # Repository (async Protocol)
│       │   ├── event_bus/            # EventBus port — sync + async
│       │   │   ├── __init__.py
│       │   │   └── async_.py
│       │   ├── logger/               # Logger port — sync + async
│       │   │   ├── __init__.py
│       │   │   └── async_.py
│       │   ├── unit_of_work/         # UnitOfWork port — sync + async
│       │   │   ├── __init__.py
│       │   │   └── async_.py
│       │   └── use_case/             # UseCase base — sync + async
│       │       ├── __init__.py
│       │       └── async_.py
│       ├── infrastructure/           # Infrastructure layer (packages)
│       │   ├── handlers/             # CommandHandler, QueryHandler — sync + async
│       │   │   ├── __init__.py
│       │   │   └── async_.py
│       │   └── repository/           # Repository with dispatch — sync + async
│       │       ├── __init__.py
│       │       └── async_.py
└── tests/                            # All tests
    ├── test_public_api.py
    ├── core/                         # Core framework tests
    │   ├── test_base_guarded.py
    │   ├── test_mutating_context.py
    │   ├── test_post_init.py
    │   ├── make_immutable/
    │   └── type_checking/
    ├── domain/                       # Domain class tests
    │   ├── test_app.py
    │   ├── test_bounded_context.py
    │   ├── test_describe.py
    │   ├── test_entity.py
    │   ├── test_event_emitter.py
    │   ├── test_service.py
    │   └── test_value_object.py
    ├── application/                  # Application layer tests
    │   ├── test_use_case.py
    │   ├── test_port.py
    │   ├── test_async_port.py
    │   └── test_async_use_case.py
    ├── infrastructure/               # Infrastructure layer tests
    │   ├── test_repository.py
    │   ├── test_handlers.py
    │   ├── test_async_handlers.py
    │   └── test_async_repository.py
    └── ...
```

## Class Hierarchy

```
BaseValidator (metaclass: ValidationModelMeta → ABCMeta)
├── UseCase                         (application use case, no reconstruct)
└── BaseGuarded                     (mutation-guarded)
    ├── Entity(ReconstructMixin, BaseGuarded)     → has reconstruct ✓
    │   └── RootEntity                            → inherits reconstruct ✓
    └── BaseSealed                  (always immutable)
        ├── ValueObject(ReconstructMixin, BaseSealed) → has reconstruct ✓
        └── Service                               → no reconstruct ✓
```

`ReconstructMixin` is only mixed into `Entity` and `ValueObject`. `Service` and `UseCase` never see `reconstruct()`.

## Key Architectural Decisions

### Single Metaclass: `ValidationModelMeta`
Only one metaclass exists in the framework — `ValidationModelMeta` on `BaseValidator`. It generates the two Pydantic models (`__validation_model__` and `__raw_model__`) at class creation time. It inherits from `ABCMeta` so that `@abstractmethod` is enforced for classes like `UseCase`.

The old `GuardedBaseMeta` and `EntityMeta` metaclasses were eliminated:
- **Method wrapping** lives in `BaseGuarded.__init_subclass__` which calls `_wrap_public_methods(cls)`
- **Root entity flag** uses `issubclass(cls, RootEntity)` — no flag variable needed
- `ValidationModelMeta.__new__` accepts `**kwargs` and forwards them to `type.__new__` for `__init_subclass__` compatibility

### Dual-Model Validation
Each user class gets two Pydantic models at class creation time:
- **Validation model** (`__validation_model__`): includes all field constraints, `@field_invariance` validators, and `@invariance` model validators
- **Raw model** (`__raw_model__`): strips all validators from annotations, excludes `@field_invariance` and `@invariance`

`__init__` uses the validation model by default. `reconstruct()` (classmethod, only on `ReconstructMixin`) uses the raw model, allowing reconstruction without re-validation.

### ContextVar Model Selection
`BaseValidator.__init__` checks a `contextvars.ContextVar` (`_use_raw_model`) to decide which model to validate against. `ReconstructMixin.reconstruct()` sets this flag before calling `cls(**kwargs)`.

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

Defined on `BaseValidator` (empty) and called from `BaseValidator.__init__`. Only runs on normal `__init__`, **not** on `reconstruct`. It executes during constructor, after fields are set via `__set_model_attributes`. For `BaseGuarded` subclasses, `__mutating_context__` already exists (created before `super().__init__()`), so:
- Public methods can be called (mutation context in INHERIT state during init)
- `_event_emitter` is already available (assigned by Pydantic via PrivateField before `__post_init__` runs via `__set_model_attributes`)
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

Works for `Entity`, `RootEntity`, `ValueObject`, `Service` (all inherit from `BaseGuarded`). Also works for `UseCase` and any `BaseValidator` subclass.

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
        aggregate_roots: Iterable[RootEntityType] | None = None,
        services: Iterable[ServiceType] | None = None,
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

### Public/Private Layer Separation

The package splits into two layers:

- **`aod.domain`, `aod.domain.validation`, `aod.exceptions`, `aod.application`, `aod.infrastructure`** — public API. These are thin re-export shims that surface symbols from `_internal`. User code and downstream tools must import from here.
- **`aod._internal.core`, `aod._internal.domain`, `aod._internal.application`, `aod._internal.infrastructure`** — private implementation. This is where everything is built and where new code goes. Not part of the supported public API and not semver-stable.

Public modules re-export from `_internal`; they contain no logic of their own. The reverse direction is never used — `_internal` never imports from `aod.domain` to avoid circular dependencies.

### `UseCase` Base Class

`UseCase` (public via `aod.application`) is the base for application-layer use cases. It extends `BaseSealed` (no `ReconstructMixin`) and provides a single abstract public method `run()` that subclasses must implement.

- `run()` has no parameters — all dependencies are passed via `__init__` (declared as Pydantic fields on the subclass)
- The class has **no public methods** other than `run`; subclasses may add private helpers
- `_event_emitter` is a `PrivateField(default_factory=EventEmitter)`, ready for direct event emission
- Auto-wired fields with Null Object defaults (no `is not None` checks):
  - `uow: UnitOfWork` — commits on success, rolls back on failure; defaults to `_NullUnitOfWork` (no-op)
  - `logger: Logger` — auto-logs completion (with event count) and failure; defaults to `_NullLogger` (no-op)
  - `event_bus: EventBus` — auto-publishes collected events after successful commit; defaults to `_NullEventBus` (no-op)

- `__init_subclass__` automatically wraps any subclass's `run` to:
  1. Open an `EventCollector` context
  2. Invoke the original `run` body
  3. Replace `self.events` with the list of captured events
- Subclasses access the events collected during the last `run` via `self.events` (public `Field(default_factory=list, init=False)`)
- Setting `self.events` during `run()` uses `object.__setattr__` internally since the assignment happens outside the mutation context, but users should not mutate `events` from outside (it's guarded by `BaseGuarded.__setattr__` and wrapped in `ImmutableList` via `make_immutable`)

Events emitted directly by the UseCase via `self._event_emitter.emit(...)` or by any entity touched during `run` are all captured and stored on the UseCase, replacing any events from previous runs.

### `Port` Base Class

`Port` (public via `aod.application`) is an abstract base class for defining dependency interfaces (ports/gateways) in the application layer. It extends `BaseGuarded`, so:
- Concrete subclasses' public methods are auto-wrapped with mutation context (can mutate fields)
- Mutations are blocked from outside
- Supports `@abstractmethod` (skipped by `_wrap_public_methods`)
- Subclasses declare fields and abstract methods that infrastructure will implement

Built-in port types (all `aod.application`):
- **`Logger`** — `debug(msg, **context)`, `info(msg, **context)`, `warning(msg, **context)`, `error(msg, **context)`
- **`EventBus`** — `publish(*events)` for publishing domain events to external handlers
- **`UnitOfWork`** — `commit()`, `rollback()`, `flush()` for transactional boundaries

### Repository Layer

`aod.application` provides the application-level contracts; `aod.infrastructure` provides the handler bases and repository:

- **`Repository`** (Protocol in `aod.application`) — structural interface with `command()` and `query()`, no inheritance needed
- **`Command[TEntity, TResult]`** / **`Query[TEntity, TResult]`** — immutable data classes for writes/reads (extend `BaseSealed`, validate `TEntity` is `RootEntity` subclass at class creation). Field types are checked at `__init_subclass__` — any field referencing a non-root `Entity` (even nested in generics like `list[Entity]`) raises `DomainException`. `Query` additionally requires its `TResult` type argument to contain at least one `RootEntity` (e.g. `Query[User, User]`, `Query[User, list[User]]`, `Query[User, tuple[int, User | None]]` are all valid).
- **`CommandHandler[C]`** / **`QueryHandler[Q]`** — abstract bases with `handle()` method; validate generic param at class creation
- **`Repository[TEntity]`** — receives `command_handlers` and `query_handlers` in `__init__`; dispatches via `command()` / `query()`; raises `DomainException` for unregistered types or duplicates
- **`UnitOfWork`** — receives `repositories: list[Repository]`, auto-builds entity-to-repo dict in `__post_init__`; provides `command()`/`query()` dispatch methods

Handler type resolution uses `extract_handler_type()` (in `type_checks/handler_checks.py`) via `get_generic_arg_from_mro` in `generic_utils.py` — works in any scope, avoids `NameError` with locally-defined handlers. Handlers live in `aod._internal.infrastructure.handlers`, imported by `repository.py` from the same module. Reusable helpers: `get_generic_arg_from_orig_bases`, `get_generic_arg_from_mro`, `validate_generic_arg_is_subclass`.

Handler type resolution uses `extract_handler_type()` (in `type_checks/handler_checks.py`) via `get_generic_arg_from_mro` in `generic_utils.py` — works in any scope, avoids `NameError` with locally-defined handlers. Handlers live in `aod._internal.infrastructure.handlers`, imported by `repository.py` from the same module. Reusable helpers: `get_generic_arg_from_orig_bases`, `get_generic_arg_from_mro`, `validate_generic_arg_is_subclass`.

Validation functions in `type_checks/handler_checks.py`:
- **`extract_handler_type(handler)`** — returns `type[Command]` or `type[Query]` via overloads; raises `DomainException` if unresolvable
- **`validate_handler_type(handler, expected_type)`** — raises `DomainException` if handler is not the expected class
- **`validate_handler_entity(handler, handler_type, repo_entity)`** — checks that `CommandHandler`/`QueryHandler` entity matches `Repository[TEntity]`'s entity
- **`handler_type_entity(handler_type)`** — extracts the entity param from a `Command`/`Query` type

Contract validation in `type_checks/contract_checks.py`:
- **`validate_fields_no_entity(cls)`** — ensures no `Command`/`Query` field references a non-root `Entity`
- **`validate_result_contains_root_entity(cls, query_type)`** — ensures `Query`'s `TResult` includes a `RootEntity`
- **`extract_root_entity(repo)`** — extracts the `RootEntity` type from a Repository's generic bases

Zero `# type: ignore` in `type_checks/`, `repository.py`, and `handlers.py`.

## Development Commands

```bash
uv run pytest code/tests -q
```

## Coding Conventions

1. **Python 3.14+** — use `|` for unions, `type[X]`, `Self`, etc.
2. **Keyword-only arguments** everywhere
3. **No comments** in source code — code should be self-documenting
4. **No emojis** unless explicitly requested by the user
5. Tests mirror source structure under `code/tests/`
6. Never import from `_internal` in user-facing code — only through `aod.domain`, `aod.domain.validation`, `aod.exceptions`, `aod.application`, `aod.infrastructure`
7. Every `__init__.py` and `async_.py` must define `__all__` to suppress `F401` ("imported but unused") warnings
8. Sync/async duality: every port, handler, use case, and repository has sync (`__init__.py`) and async (`async_.py`) versions with the same class name. Async versions inherit from sync counterparts where possible (e.g., `async_.CommandHandler` inherits from `handlers.CommandHandler`)

## When Modifying This Code

- If you change the dual-model system, update `model_maker.py` and verify `test_base_validator.py`
- If you change the mutation system, update `base_guarded.py` (including `_wrap_public_methods`) and verify `test_base_guarded.py` + `test_make_immutable.py`
- If you change `__post_init__`, update `base_validator.py` (definition and trigger), and verify `test_post_init.py`
- If you change `reconstruct()`, update `reconstructable.py` and verify `test_post_init.py` + `test_base_validator.py`
- If you change domain classes, check `test_event_emitter.py`, `test_entity.py`, `test_value_object.py`
- If you change type checks, update `type_handlers/extractors.py` and/or `type_handlers/checks` and verify tests
- If you change bounded context logic, update `bounded_context.py` and check `test_bounded_context.py`
- If you change the repository layer, update `repository.py` and/or `handlers.py` and verify `test_repository.py`
- If you change validation functions, update `type_checks/` and verify `test_repository.py`
- If you change the application layer, update `port.py` and/or `use_case.py` and verify `test_port.py` / `test_use_case.py`
- If you change async counterparts (in `async_.py` files), update both sync and async test files
- Always add `__all__` to every `__init__.py` and `async_.py` to avoid `F401` lint warnings
- Always run all tests before committing
- `Event.emitted_at` is the timestamp field.

## Dependencies

- **Runtime**: `pydantic>=2.12.4`, `typing-inspect>=0.9.0`
- **Dev**: `ruff`, `ty`, `pre-commit`, `pytest`
- **Build**: `setuptools`, `wheel`

## Test Count

398 tests

## At the end of a task

Update docs, AGENTS.md and the SKILLS.md
