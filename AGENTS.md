# attack-on-domain — Agent Guide

## Overview

`attack-on-domain` is a Python 3.14+ library providing Domain-Driven Design building blocks using Pydantic v2 under the hood. It implements entities, value objects, bounded contexts, domain events, and a dual-model validation system.

**Source code is under `code/`** — this directory is mapped as the package root in `pyproject.toml`.

## Project Structure

```
code/
├── aod/                              # Package root
│   ├── __init__.py                   # Empty package marker
│   ├── events.py                     # Public: Event, EventCollector (cross-layer)
│   ├── py.typed                      # PEP 561 marker
│   ├── domain/                       # Public domain layer (re-exports from _internal)
│   │   ├── __init__.py               # Re-exports: App, BoundedContext, Entity, RootEntity, Service, ValueObject, Field, PrivateField, DomainException
│   │   └── validation/               # Public: AfterValidator, BeforeValidator, field_invariance, invariance, inherit_context
│   ├── exceptions/__init__.py        # Public: DomainException, MutationForbiddenException
│   └── _internal/                    # Private — not semver-stable
│       ├── core/                     # Framework internals
│       │   ├── async_utils.py        # should_await (sync/async bridge)
│       │   ├── base_validator.py     # ValidationModelMeta + BaseValidator
│       │   ├── reconstructable.py    # ReconstructMixin (reconstruct classmethod)
│       │   ├── base_sealed.py        # BaseSealed (always-blocked mutation)
│       │   ├── base_guarded/         # BaseGuarded, MutatingContext, make_immutable subsystem
│       │   ├── event_emitter.py      # Event, EventEmitter, EventCollector
│       │   ├── model_maker.py        # Dual Pydantic model generation
│       │   ├── domain_exception.py       # DomainException hierarchy
│       │   ├── application_exception.py  # ApplicationException hierarchy
│       │   ├── infrastructure_exception.py  # InfrastructureException hierarchy
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
│       │   └── handler_checks.py    # extract_handler_type, validate_handler_type, validate_handler_entity, handler_type_entity
│       └── domain/                   # DDD domain primitives (implementation)
│           ├── value_object.py
│           ├── entity.py
│           ├── service.py
│           ├── app.py
│           ├── bounded_context.py
│           └── describe.py
│       ├── application/              # Application layer (packages)
│       │   ├── port.py               # Port base class (abstract, mutable-from-inside)
│       │   ├── projection/           # Projection data class + ProjectionStore Protocol
│       │   │   ├── __init__.py       # ProjectionQuery, ProjectionCommand, ProjectionStore
│       │   │   ├── projection.py     # ProjectionQuery[T], ProjectionCommand
│       │   │   ├── projection_store.py  # ProjectionStore (Protocol)
│       │   │   └── async_.py         # ProjectionStore (async Protocol)
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
│       │   │   ├── unit_of_work.py   # _UnitOfWorkBase (shared logic), UnitOfWork (sync)
│       │   │   └── async_.py         # UnitOfWork (async, accepts sync/async repos + stores)
│       │   └── use_case/             # UseCase base — sync + async
│       │       ├── __init__.py
│       │       └── async_.py
│       ├── infrastructure/           # Infrastructure layer (packages)
│       │   ├── handlers/             # CommandHandler, QueryHandler — sync + async
│       │   │   ├── __init__.py
│       │   │   └── async_.py
│       │   ├── projection/           # ProjectionHandler + ProjectionStore — sync + async
│       │   │   ├── __init__.py
│       │   │   ├── projection_handler.py  # ProjectionQueryHandler + ProjectionCommandHandler (sync)
│       │   │   ├── projection_store.py    # ProjectionStore (concrete, sync)
│       │   │   └── async_.py         # ProjectionHandler + ProjectionStore (async)
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
    │   ├── test_projection.py        # Projection data class (no entity constraints)
    │   ├── test_use_case.py
    │   ├── test_port.py
    │   ├── test_async_port.py
    │   └── test_async_use_case.py
    ├── infrastructure/               # Infrastructure layer tests
    │   ├── test_projection_handler.py
    │   ├── test_async_projection_handler.py
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
All framework exceptions are re-exported from `aod.exceptions`. The hierarchy is also available per-layer via `aod.domain.exceptions`, `aod.application.exceptions`, and `aod.infrastructure.exceptions`. The base exceptions are exported directly on each layer's package:

- `from aod.domain import DomainException`
- `from aod.application import ApplicationException`
- `from aod.infrastructure import InfrastructureException`

The hierarchy:

**Bases:**
- `DomainException` — base for all domain rule violations
- `ApplicationException` — base for application layer errors (UoW dispatch)
- `InfrastructureException` — base for infrastructure layer errors (repository dispatch, projection store, handlers)

**`DomainException` subclasses:**
- `MutationForbiddenException(DomainException)` — mutation outside allowed context
- `InvarianceException(DomainException, ValueError)` — field/model invariance violated
- `InvalidCommandFieldTypeError` — Command/Query field references non-root Entity
- `InvalidQueryResultTypeError` — `Query` TResult does not include a `RootEntity`
- `InvalidGenericTypeArgError` — generic argument fails its constraint
- `InvalidProjectionTypeError` — projection type is not `ReadModel` or `None`
- `InvalidEntityTypeError` — not an `Entity` subclass
- `InvalidRootEntityTypeError` — `Entity` but not `RootEntity`
- `InvalidServiceTypeError` — not a `Service` subclass
- `ClassExpectedError` — instance given where class required
- `InvalidNestedTypeError` — Entity field references forbidden domain type
- `InvalidServiceParameterError` — Service method parameter has disallowed type
- `DuplicateDomainTypeError` — domain type registered in >1 `BoundedContext`
- `HandlerTypeMismatchError` — handler not a subclass of expected handler base
- `HandlerEntityMismatchError` — handler's entity does not match repository's entity
- `UnresolvableHandlerTypeError` — cannot determine Command/Query type from handler

**`ApplicationException` subclasses:**
- `ProjectionStoreNotConfiguredError` — no `ProjectionStore` in UoW
- `UnresolvableEntityError` — cannot determine `RootEntity` from Command/Query
- `RepositoryNotRegisteredError` — no repository for the entity

**`InfrastructureException` subclasses:**
- `UnresolvableProjectionTypeError` — cannot determine projection type from handler
- `DuplicateProjectionHandlerError` — duplicate handler in `ProjectionStore`
- `ProjectionHandlerNotFoundError` — no handler for projection type
- `DuplicateHandlerError` — duplicate handler in `Repository`
- `HandlerNotFoundError` — no handler for Command/Query in `Repository`
- `HandlerResultTypeError` — handler returned wrong type

> For details on when each is raised, see `docs/core/exceptions.md`.

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
  - `uow: UnitOfWork` — auto-commits on success (only if `is_dirty`), auto-rollbacks on failure; defaults to `_NullUnitOfWork` (no-op)
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
- **`UnitOfWork`** — receives `repositories: list[Repository]`, auto-builds entity-to-repo dict in `__post_init__`; `command()` and `query()` dispatch to reposito/query handlers and also handle `ProjectionCommand`/`ProjectionQuery` via `projection_store`. Has `is_dirty` flag (set True after command).

Handler type resolution uses `extract_handler_type()` (in `type_checks/handler_checks.py`) via `get_generic_arg_from_mro` in `generic_utils.py` — works in any scope, avoids `NameError` with locally-defined handlers. Validators: `handler_type_entity`, `validate_handler_type`, `validate_handler_entity`. Reusable helpers: `get_generic_arg_from_orig_bases`, `get_generic_arg_from_mro`, `validate_generic_arg_is_subclass`.

Validation functions in `type_checks/handler_checks.py`:
- **`extract_handler_type(handler, handler_types)`** — returns `type[Command]` or `type[Query]`; callers pass the handler-type tuple (sync or async) as `handler_types`; raises `DomainException` if unresolvable
- **`validate_handler_type(handler, expected_type)`** — raises `DomainException` if handler is not the expected class
- **`validate_handler_entity(handler, handler_type, repo_entity)`** — checks that `CommandHandler`/`QueryHandler` entity matches `Repository[TEntity]`'s entity
- **`handler_type_entity(handler_type)`** — extracts the entity param from a `Command`/`Query` type

Contract validation in `type_checks/contract_checks.py`:
- **`validate_fields_no_entity(cls)`** — ensures no `Command`/`Query` field references a non-root `Entity`
- **`validate_result_contains_root_entity(cls, query_type)`** — ensures `Query`'s `TResult` includes a `RootEntity`
- **`extract_root_entity(repo)`** — extracts the `RootEntity` type from a Repository's generic bases

### `ProjectionQuery[T]` / `ProjectionCommand` / `ProjectionStore`

Analogous to `Query`/`Command` but for read/write projections:

- **`ProjectionQuery[T]`** (`aod.application`) — read-only projection. `BaseSealed, Generic[T]` data class. No `__init_subclass__` validation — fields can reference any type. `T` is the return type (like `Query`).
- **`ProjectionCommand`** (`aod.application`) — write-only projection. `BaseSealed` data class. Carries write data in its own fields (like `Command`). No type parameter — `handle()` returns `None`.
- **`ProjectionStore`** (`aod.application`) — `Protocol` with `query(query: ProjectionQuery[T]) -> T` and `command(command: ProjectionCommand) -> None`. Sync and async versions available.
- **`ProjectionQueryHandler[PQ]`** (`aod.infrastructure`) — abstract base with `handle(query: PQ) -> object`. Validates `PQ` is a `ProjectionQuery` subclass.
- **`ProjectionCommandHandler[PC]`** (`aod.infrastructure`) — abstract base with `handle(command: PC) -> None`. Validates `PC` is a `ProjectionCommand` subclass.
- **`ProjectionStore`** (`aod.infrastructure`) — concrete dispatcher: receives both handler types, validates duplicates in `__post_init__`, dispatches via `query()` / `command()`.

Unlike `CommandHandler`/`QueryHandler`, projection handlers are **not** registered in a `Repository`. They live in `aod.infrastructure.projection` and are consumed independently via `ProjectionStore`.

### `should_await` Helper

`aod._internal.core.async_utils.should_await(value)` — bridges sync and async calls:
- If `value` is a coroutine, awaits and returns the result
- Otherwise returns the value as-is

Used by async `UnitOfWork.command/query` and async `UseCase` wrapper (imported as `awaiter`). This allows async UoW to accept both sync and async repositories/stores without knowing which at call time.

Zero `# type: ignore` in `type_checks/`, `repository.py`, and `handlers.py`.

### Test Doubles (`aod.testing.doubles`)

Spy classes for testing application-layer ports, organized by layer under `aod/testing/doubles/`:

```
aod/testing/
├── __init__.py
└── doubles/
    ├── __init__.py                     # Re-exports all (sync + async)
    ├── application/
    │   ├── __init__.py                 # Re-exports from modules
    │   ├── logger.py                   # LogEntry, SpyLogger
    │   ├── event_bus.py                # SpyEventBus
    │   ├── unit_of_work.py             # SpyUnitOfWork
    │   └── async_.py                   # AsyncSpyLogger, AsyncSpyEventBus, AsyncSpyUnitOfWork
    └── infrastructure/
        └── __init__.py                 # Placeholder for future doubles
```

All spy classes use `PrivateField` instead of `object.__setattr__` to stay consistent with the framework's mutation-guarding system. Public methods are auto-wrapped by `_wrap_public_methods`, so in-place mutations (`.append()`, `.extend()`) inside them work transparently.

- **`SpyLogger`** — captures `LogEntry` objects; `.entries` returns a snapshot copy
- **`SpyEventBus`** — captures published `Event` objects; `.published` returns a snapshot copy
- **`SpyUnitOfWork`** — tracks `committed`, `rolled_back`, `flushed` booleans; has `set_dirty()` to mark `is_dirty`

Import from `aod.testing.doubles` (sync) or from individual modules.

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
- If you change the projection layer, update `projection_handler.py` / `projection_store.py` (both application and infrastructure) and verify `test_projection.py` / `test_projection_handler.py` / `test_async_projection_handler.py`
- If you change the repository layer, update `repository.py` and/or `handlers.py` and verify `test_repository.py`
- If you change validation functions, update `type_checks/` and verify `test_repository.py`
- If you change the application layer, update `port.py` and/or `use_case.py` and verify `test_port.py` / `test_use_case.py`
- If you change the UnitOfWork, update `unit_of_work.py` (sync + async) and verify `test_port.py` / `test_async_port.py` (includes `is_dirty` tests)
- If you change async counterparts (in `async_.py` files), update both sync and async test files
- If you change `should_await` in `async_utils.py`, verify `test_use_case.py` / `test_async_use_case.py` (used as `awaiter`) and `test_async_port.py`
- Always add `__all__` to every `__init__.py` and `async_.py` to avoid `F401` lint warnings
- Always run all tests before committing
- `Event.emitted_at` is the timestamp field.
- **No inline imports in tests** — every import must be at the top of the file. Test-local classes are fine, but imports from `aod`, `pydantic`, `unittest`, `types`, etc. must be at module level.

## Dependencies

- **Runtime**: `pydantic>=2.12.4`, `typing-inspect>=0.9.0`
- **Dev**: `ruff`, `ty`, `pre-commit`, `pytest`
- **Build**: `setuptools`, `wheel`

## Test Count

582 tests

## At the end of a task

Update docs, AGENTS.md and the SKILLS.md
