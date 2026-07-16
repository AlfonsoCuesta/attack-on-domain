# attack-on-domain — Agent Guide

## Overview

`attack-on-domain` is a Python 3.14+ library providing Domain-Driven Design building blocks using Pydantic v2 under the hood. It implements entities, value objects, bounded contexts, domain events, and a validation system.

**Source code is under `code/`** — this directory is mapped as the package root in `pyproject.toml`.

**For how to *use* the library** (workflow steps, code examples, common mistakes), load `skills/attack-on-domain/SKILL.md`. This file covers how to *build* the library itself.

## Project Structure

```
code/
├── aod/                              # Package root
│   ├── __init__.py                   # Empty package marker
│   ├── events.py                     # Public: Event, EventCollector (cross-layer)
│   ├── py.typed                      # PEP 561 marker
│   ├── domain/                       # Public domain layer (re-exports from _internal)
│   │   ├── __init__.py               # Re-exports: Entity, RootEntity, Service, ValueObject, Field, PrivateField, DomainException
│   │   └── validation/               # Public: AfterValidator, BeforeValidator, field_invariance, invariance, mutable
│   ├── exceptions/__init__.py        # Public: all domain/app/infra exceptions
│   ├── testing/                       # Public testing utilities
│   │   ├── __init__.py                # FakeDomain, build, events_of, assert_*
│   │   └── doubles/
│   │       ├── __init__.py            # Empty (package marker)
│   │       ├── application/
│   │       │   ├── __init__.py        # SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache
│   │       │   ├── spies.py          # Generated via port_stub (replaces hand-written spies)
│   │       │   └── async_/
│   │       │       └── __init__.py    # Async re-exports (plain names)
│   └── _internal/                    # Private — not semver-stable
│       ├── core/                     # Framework internals
│       │   ├── async_utils.py        # should_await (sync/async bridge)
│       │   ├── base_validator.py     # ValidationModelMeta + BaseValidator
│       │   ├── reconstructable.py    # ReconstructMixin (reconstruct classmethod)
│       │   ├── base_sealed.py        # BaseSealed (always-blocked mutation)
│       │   ├── base_guarded/         # BaseGuarded, MutatingContext, make_immutable subsystem
│       │   ├── base_behaviour.py     # BaseBehaviour (allows mutation inside methods)
│       │   ├── base_operation.py     # BaseOperation(BaseBehaviour) — adds _event_emitter, events, _loggers, _event_buses
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
│       │       ├── fields/fields.py      # Field(), PrivateField() wrappers
│       │       └── invariances/invariances.py  # field_invariance, invariance, is_validator
│       └── domain/                   # DDD domain primitives (implementation)
│           ├── value_object.py
│           ├── entity.py
│           ├── service.py
│           ├── app.py
│           ├── bounded_context.py
│           └── describe.py
│       ├── application/              # Application layer (packages)
│       │   ├── port.py               # Port base class (abstract, mutable-from-inside)
│       │   ├── cache/                # Cache system — sync + async
│       │   │   ├── __init__.py
│       │   │   ├── cache.py           # Cache(Port), AsyncCache(Port), BaseCache, _CacheEntry
│       │   │   ├── cache_key.py       # CacheKey, CacheInvalidation
│       │   │   └── null_cache.py      # NullCache (no-op default)
│       │   ├── contracts/            # Command, Query — application contracts
│       │   │   ├── __init__.py       # Command, Query
│       │   │   └── contracts.py      # Command(BaseSealed), Query(BaseSealed) with field validation
│       │   ├── event_bus/            # EventBus port — sync + async
│       │   │   ├── __init__.py
│       │   │   └── event_bus.py       # EventBus(Port) + AsyncEventBus(Port)
│       │   ├── logger/               # Logger port — sync + async
│       │   │   ├── __init__.py
│       │   │   └── logger.py          # Logger(Port) + AsyncLogger(Port)
│       │   ├── unit_of_work/         # UnitOfWork (concrete, sessions + caches)
│       │   │   ├── __init__.py
│       │   │   └── unit_of_work.py   # _UnitOfWorkBase (shared logic), UnitOfWork (sync), AsyncUnitOfWork (async, accepts sync/async sessions)
│       │   └── use_case/             # UseCase base — sync + async
│       │       ├── __init__.py
│       │       └── use_case.py       # UseCase(BaseOperation) + AsyncUseCase(BaseOperation)
│   ├── infrastructure/           # Infrastructure layer (packages)
│   │   ├── session/              # Session (database abstraction)
│   │   │   ├── __init__.py
│   │   │   └── session.py        # Session(Port) + AsyncSession(Port)
│   │   ├── handlers/             # CommandHandler, QueryHandler — sync + async
│   │   │   ├── __init__.py
│   │   │   ├── base_handler.py   # BaseHandler + AsyncBaseHandler
│   │   │   └── handlers.py       # CommandHandler, QueryHandler, AsyncCommandHandler, AsyncQueryHandler
│   │   ├── projection/           # Projection models + base classes — sync + async
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # ReadModel(BaseSealed), WriteModel(BaseSealed)
│   │   │   └── projection.py     # ProjectionBase, ReadProjectionBase, WriteProjectionBase, ReadProjection, WriteProjection, Projection, AsyncReadProjection, AsyncWriteProjection, AsyncProjection
│   │   ├── container/            # AdapterContainer, PortManager, SessionManager, HandlerManager
│   │   │   ├── __init__.py
│   │   │   ├── container.py      # AdapterContainer orchestrator
│   │   │   ├── types.py          # Type helpers and aliases
│   │   │   ├── port_manager.py   # Port index, resolution, injection
│   │   │   ├── session_manager.py  # Session lifecycle, UoW creation
│   │   │   └── handler_manager.py  # Handler discovery, validation, instantiation
│       └── testing/                  # Testing utilities (implementation)
│           ├── __init__.py           # Re-exports: DomainType, FakeDomain, build, helpers
│           ├── helpers.py            # build(), events_of(), assert_event_emitted(), etc.
│           ├── doubles/              # Spy implementations
│           │   ├── __init__.py       # Re-exports all (sync + async)
│           │   ├── stubs.py          # port_stub() generator
│           │   ├── async_/
│           │   │   └── __init__.py   # Re-exports async spies from application
│           │   ├── application/
│           │   │   ├── __init__.py
│           │   │   └── spies.py      # All Spy* classes via port_stub (replaces 4 hand-written files)
│           │   └── infrastructure/
│           │       ├── __init__.py
│           │       ├── container.py  # SpyAdapterContainer
│           │       ├── fakes.py      # FakeSessionManager, FakeHandlerManager, FakePortManager
│           │       └── session.py    # SpySession, SpyAsyncSession
│           └── faker/
│               ├── __init__.py
│               └── faker.py          # DomainType, FakeDomain
│       └── schema/                   # Schema system — introspection + docs generation
│           ├── __init__.py           # Public: App, BoundedContext, Module, Infrastructure, AutoDoc, all Doc types
│           ├── app.py                # App: main entry point, aggregates modules
│           ├── bounded_context.py    # BoundedContext: aggregate_roots, services, use_cases, contracts, ports
│           ├── infrastructure.py     # Infrastructure: handlers, sessions, projections, ports
│           ├── module.py             # Module: validates handler-port wiring
│           ├── describe_utils.py     # extract_fields(), extract_methods(), extract_params()
│           ├── docs/                 # Doc dataclasses for each schema type
│           │   ├── __init__.py
│           │   ├── app_doc.py        # AppDoc.from_app()
│           │   ├── module_doc.py     # ModuleDoc.from_module()
│           │   ├── bounded_context_doc.py  # BoundedContextDoc.from_bounded_context()
│           │   ├── entity_doc.py     # EntityDoc.from_entity()
│           │   ├── root_entity_doc.py  # RootEntityDoc.from_root_entity()
│           │   ├── value_object_doc.py  # ValueObjectDoc.from_value_object()
│           │   ├── service_doc.py    # ServiceDoc.from_service()
│           │   ├── handler_doc.py    # HandlerDoc.from_handler()
│           │   ├── handler_port_doc.py  # HandlerPortDoc.from_handler_port()
│           │   ├── contract_doc.py   # ContractDoc.from_contract()
│           │   ├── port_doc.py       # PortDoc.from_port()
│           │   ├── session_doc.py    # SessionDoc.from_session()
│           │   ├── projection_doc.py  # ProjectionDoc.from_projection()
│           │   ├── use_case_doc.py   # UseCaseDoc.from_use_case()
│           │   ├── infrastructure_doc.py  # InfrastructureDoc.from_infrastructure()
│           │   └── generic_docs.py   # FieldDoc, MethodDoc, ParamDoc, type_str(), default_str()
│           └── render/               # Zensical site generator
│               ├── __init__.py       # Public: AutoDoc
│               ├── auto_doc.py       # AutoDoc: generates zensical .md site from App
│               ├── styles/
│               │   └── extra.css     # Default CSS for generated site
│               └── overrides/
│                   └── main.html     # Default template override (hides sidebar)
└── tests/                            # All tests
    ├── test_public_api.py
    ├── core/                         # Core framework tests
    │   ├── test_base_guarded.py
    │   ├── test_base_operation_port_check.py
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
    │   ├── test_async_handlers.py
    │   ├── test_cache.py
    │   ├── test_container.py
    │   ├── test_inject.py
    │   ├── test_projection_classes.py
    │   ├── test_session.py
    │   └── test_unit_of_work.py
    └── e2e/                          # End-to-end real-world usage tests
        ├── test_ecommerce.py         # E-commerce domain: VOs, entities, bounded context, app, use case, container, inject, faker, build
        ├── test_invariances.py       # field_invariance, invariance, check_invariant helper
        ├── test_handler_injection.py # Application-layer Protocol handlers, container wiring with handlers + ports
        ├── test_projections.py       # ReadProjection, WriteProjection, Projection, async variants, injection
        └── test_mutation_rules.py    # _can_mutate, BaseGuarded mutation rules, immutable proxies, nested entities
```

## Class Hierarchy

```
BaseValidator (metaclass: ValidationModelMeta -> ABCMeta)
+-- BaseGuarded                     (mutation-guarded)
    +-- BaseBehaviour               (extends BaseGuarded -- allows mutation inside methods)
    |   +-- BaseOperation           (adds _event_emitter, events, _loggers, _event_buses, _caches)
    |   |   +-- UseCase             -> +_uow, +run()
    |   |   +-- AsyncUseCase        -> +_uow, +async run()
    |   |   +-- ProjectionBase
    |   |   |   +-- ReadProjectionBase
    |   |   |   |   +-- ReadProjection       -> +read()
    |   |   |   |   +-- AsyncReadProjection  -> +async read()
    |   |   |   +-- WriteProjectionBase
    |   |   |   |   +-- WriteProjection      -> +write()
    |   |   |   |   +-- AsyncWriteProjection -> +async write()
    |   |   |   +-- Projection               -> +read() +write()
    |   |   |   +-- AsyncProjection          -> +async read() +write()
    |   |   +-- Service (in domain, does NOT inherit BaseOperation -- just BaseBehaviour)
    |   +-- BaseSealed              (always blocks mutation)
    |       +-- ValueObject(ReconstructMixin, BaseSealed) -> has reconstruct
    |       +-- Event
    |       +-- Command
    |       +-- Query
    +-- BaseGuarded (direct inheritance for Port, Session, etc.)
```

## Key Architectural Decisions

### Single Metaclass: `ValidationModelMeta`
Only one metaclass exists -- `ValidationModelMeta` on `BaseValidator`. It generates two Pydantic models (`__validation_model__` and `__raw_model__`) at class creation time. It inherits from `ABCMeta` so that `@abstractmethod` is enforced for classes like `UseCase`.

The old `GuardedBaseMeta` and `EntityMeta` metaclasses were eliminated:
- **Method wrapping** lives in `BaseGuarded.__init_subclass__` which calls `_wrap_public_methods(cls)`
- **Root entity flag** uses `issubclass(cls, RootEntity)` -- no flag variable needed
- `ValidationModelMeta.__new__` accepts `**kwargs` and forwards them to `type.__new__` for `__init_subclass__` compatibility

### Validation System
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
- Abstract methods (marked with `@abstractmethod`)

### Immutable Proxies via `make_immutable`
When an attribute is read outside a mutation context, `BaseGuarded.__getattribute__` returns `make_immutable(value)`:
- `list` -> `ImmutableList` (blocks append, extend, __setitem__, etc.)
- `dict` -> `ImmutableDict` (blocks __setitem__, update, pop, etc.)
- `set` -> `ImmutableSet` (blocks add, remove, discard, etc.)
- Custom objects -> dynamically created `Immutable{ClassName}` subclass (wraps getattr, blocks setattr/delattr/mutating dunders)

### Event Collection via ContextVar
`EventEmitter.emit()` always appends to its local list. If an `EventCollector` context manager is active (via ContextVar), it also appends to the collector's list. This enables aggregate-level event collection without explicit child traversal.

### `__post_init__` Hook (mechanism)
Defined on `BaseValidator` (empty) and called from `BaseValidator.__init__`. Only runs on normal `__init__`, **not** on `reconstruct`. It executes after fields are set via `__set_model_attributes`. For `BaseGuarded` subclasses, `__mutating_context__` already exists (created before `super().__init__()`), so:
- Public methods can be called (mutation context in INHERIT state during init)
- `_event_emitter` is already available (assigned by Pydantic via PrivateField before `__post_init__` runs)
- Field mutation is allowed during the hook

Works for `Entity`, `RootEntity`, `ValueObject`, `Service` (all inherit from `BaseGuarded`). Also works for `UseCase` and any `BaseValidator` subclass.

`__post_init__` vs `@invariance` / `@field_invariance`: both run at construction but serve different purposes. Post-init has `self` and can mutate fields; invariance validators receive `cls` and the raw value. See `docs/domain/entities.md`.

### Identity Field (enforcement)
`Entity.__init_subclass__` enforces at class creation time:
- Zero fields with `Field(id=True)` -> `NoIdentityFieldException`
- Multiple fields with `Field(id=True)` -> `TooManyIdentityFieldsException`

### Equality Behavior (mechanism)
- **ValueObject**: compared by all public fields (`==` compares every annotated field; `PrivateField` attributes excluded)
- **Entity / RootEntity**: compared only by their identity field

### `Entity.can_mutate()` and `@mutable` (mechanism)
`Entity` exposes public `can_mutate()`. `BaseGuarded._is_mutation_allowed` calls `_can_mutate()` which delegates to `can_mutate()`. `ValueObject` and `BaseSealed` always block mutation.

The `@mutable` decorator (exposed as `from aod.domain.validation import mutable`) marks a method to inherit the mutation context from its caller, bypassing the `can_mutate()` guard. Internally called `inherit_context`. Needed for methods like `lock()`/`unlock()` that must mutate when the entity is locked.

### Type Checking System (`type_handlers/`)
Three check functions enforce DDD type constraints at `BoundedContext` construction:

- `check_entity` / `check_root_entity`: raises `InvalidNestedTypeError` if any field references `RootEntity`
- `check_value_object`: raises `InvalidNestedTypeError` if any field references `Entity` or `RootEntity`. Also raises `InvalidValueObjectFieldError` at class creation if any field has `Field(id=True)`
- `check_service`: iterates public methods via `inspect.getmembers`, resolves forward refs via `typing.get_type_hints`, raises `InvalidServiceParameterError` if any param or return type is a non-root `Entity`

### BoundedContext Constructor (tech details)
Accepts `aggregate_roots` (RootEntity subclasses) and `services` (Service subclasses). Discovers entities and value objects recursively via `_discover_types()`: starts from each root entity, gets `typing.get_type_hints()`, extracts types via `extract_types_from_annotation()`, recurses through discovered Entity and ValueObject fields. Runs check functions on all discovered types. Use in the entry point (container), not in `domain/__init__.py`.

### Public/Private Layer Separation
Two layers:
- **`aod.domain`, `aod.domain.validation`, `aod.exceptions`, `aod.application`, `aod.infrastructure`** -- public API. Thin re-export shims that surface symbols from `_internal`. User code imports from here.
- **`aod.application.async_`**, **`aod.infrastructure.async_`** -- aggregated async counterparts (sync name for async class, e.g. `from aod.application.async_ import Cache` for `AsyncCache`).
- **`aod._internal.*`** -- private implementation. Not part of public API, not semver-stable.

Public modules re-export from `_internal`; `_internal` never imports from `aod.domain` (avoids circular deps).

### Public exceptions in `aod.exceptions`
All framework exceptions re-exported from `aod.exceptions`. Per-layer base exceptions also exported:
- `from aod.domain import DomainException`
- `from aod.application import ApplicationException`
- `from aod.infrastructure import InfrastructureException`

**DomainException subclasses:**
- `MutationForbiddenException` -- mutation outside allowed context
- `InvarianceException(DomainException, ValueError)` -- field/model invariance violated
- `InvalidCommandFieldTypeError` -- Command/Query field references non-root Entity
- `InvalidValueObjectFieldError` -- ValueObject has `Field(id=True)`
- `InvalidQueryResultTypeError` -- Query TResult does not include a RootEntity
- `InvalidGenericTypeArgError` -- generic argument fails its constraint
- `InvalidEntityTypeError` -- not an Entity subclass
- `InvalidRootEntityTypeError` -- Entity but not RootEntity
- `InvalidServiceTypeError` -- not a Service subclass
- `ClassExpectedError` -- instance given where class required
- `InvalidNestedTypeError` -- Entity field references forbidden domain type
- `InvalidServiceParameterError` -- Service method parameter has disallowed type
- `DuplicateDomainTypeError` -- domain type registered in >1 BoundedContext
- `ModelValidationError` -- Pydantic validation failed during construction (wraps ValidationError; InvarianceException re-raised directly)

**ApplicationException subclasses:**
- `UnresolvableEntityError` -- cannot determine RootEntity from Command/Query
- `CommitOutsideUnitOfWorkError` -- commit outside a UnitOfWork context
- `InvalidUseCasePortFieldError` -- UseCase field is not a Port subclass
- `InvalidHandlerPortFieldError` -- HandlerProtocol port on a UseCase missing its generic type argument

**InfrastructureException subclasses:**
- `AbstractSessionTypeError` -- field uses `Session`/`AsyncSession` directly instead of concrete type
- `HandlerResultTypeError` -- handler returned wrong type
- `HandlerModelError` -- handler class missing required field
- `PortNotFoundError` -- port type not registered on container
- `SessionNotFoundError` -- session type not registered on container

### `UseCase` Base Class (internals)
`UseCase` extends `BaseOperation`. Key mechanics:
- **`_uow` is private** -- auto-created via `PrivateField(default_factory=UnitOfWork)`, auto-registers all handler fields in `__init__`
- **`__init_subclass__`** wraps `run` to: (1) open EventCollector context, (2) invoke original run, (3) replace `self.events` with captured list
- **Field validation**: `BaseOperation.__init_subclass__` checks fields. Only `Port` subclasses allowed. `BaseHandler`/`AsyncBaseHandler` and `Session`/`AsyncSession` rejected. `AppCommandHandler[T]`/`AppQueryHandler[T]` accepted (inherit from `HandlerProtocol(Port)`). Non-Port fields raise `InvalidUseCasePortFieldError`.
- **`__skip_port_check__`** check uses `cls.__dict__.get("__skip_port_check__")` -- only current class's own dict, not inherited
- **Container sessions**: `AdapterContainer.sessions` holds session **classes**, not instances. `get_session()` instantiates and caches. `HandlerManager` creates handler instances with session instances; UseCase's `UnitOfWork` collects them via `add_handler()`.

### `Port` Base Class (internals)
`Port` extends `BaseGuarded`:
- Concrete subclasses' public methods auto-wrapped with mutation context
- Supports `@abstractmethod` (skipped by `_wrap_public_methods`)
- Built-in port types: `Logger`/`AsyncLogger`, `EventBus`/`AsyncEventBus`, `Cache`/`AsyncCache`

### `HandlerProtocol` (runtime checking)
All application-layer handler types (`CommandHandler`, `QueryHandler`, etc.) inherit from `HandlerProtocol(Port)`. Infrastructure handler types inherit from both `BaseHandler` and the corresponding app-layer `HandlerProtocol`.

`HandlerProtocol.__init_subclass__` wraps `handle()` with type checker: verifies command/query matches generic type parameter. Raises `TypeError` on mismatch.

### Contracts (`Command` / `Query`) (validation)
`Command[TEntity, TResult]` / `Query[TEntity, TResult]` extend `BaseSealed`. Validate `TEntity` is `RootEntity` subclass at class creation. Field types checked: any field referencing non-root `Entity` raises `DomainException`. `Query` additionally requires `TResult` to contain at least one `RootEntity`.

### CommandHandler / QueryHandler (result checking)
`BaseHandler` has `_wrap_handle()` that validates `handle()` return type against generic parameter at runtime using `get_last_generic_arg`.

### Projection System (tech details)
`ProjectionBase(BaseOperation)` inherits `_event_emitter`, `events`, `logger`, `event_bus`. Fields must be `Port` subclasses (except session fields). `HandlerProtocol` rejected via `__not_allowed_port_types__ = (HandlerProtocol,)`. Multiple session fields allowed with concrete types. `ProjectionBase.__init_subclass__` calls `typing.get_type_hints(cls)` and raises `AbstractSessionTypeError` for direct `Session`/`AsyncSession` fields.

`ReadProjectionBase`/`WriteProjectionBase` wrap `read()`/`write()` with EventCollector + log + event_bus publish. `WriteProjectionBase` additionally wraps with `CommitContext` + rollback on failure.

### Test Doubles (directory structure)
```
aod/_internal/testing/
+-- __init__.py                     # Re-exports all spies
+-- helpers.py                      # build(), events_of(), assert_event_emitted()
+-- doubles/
|   +-- __init__.py                 # Re-exports all (sync + async)
|   +-- stubs.py                    # port_stub() generator
|   +-- async_/__init__.py          # Async spy re-exports
|   +-- application/
|   |   +-- __init__.py
|   |   +-- spies.py                # All Spy* classes via port_stub
|   +-- infrastructure/
|       +-- __init__.py
|       +-- container.py            # SpyAdapterContainer
|       +-- fakes.py                # FakeSessionManager, FakeHandlerManager, FakePortManager
|       +-- session.py              # SpySession, SpyAsyncSession
+-- faker/
    +-- __init__.py
    +-- faker.py                    # DomainType, FakeDomain
```

Public re-exports at `aod/testing/`.

## Development Commands

```bash
make check          # lint + typecheck + test-all
uv run pytest code/tests -q   # tests only
make lint           # ruff check
make typecheck      # pyright (when configured)
```

## Coding Conventions

1. **Python 3.14+** -- use `|` for unions, `type[X]`, `Self`, etc.
2. **Keyword-only arguments** everywhere
3. **No comments** in source code -- code should be self-documenting
4. **No emojis** unless explicitly requested by the user
5. Tests mirror source structure under `code/tests/`
6. Never import from `_internal` in user-facing code -- only through `aod.domain`, `aod.domain.validation`, `aod.exceptions`, `aod.application`, `aod.infrastructure`
7. Every `__init__.py` must define `__all__` to suppress `F401` ("imported but unused") warnings. Public `async_.py` aggregators also define `__all__`.
8. Sync/async duality: every port, handler, and use case has sync and async versions. Sync classes keep the base name (`Cache`, `Session`, `UnitOfWork`, `CommandHandler`, etc.), async classes use the `Async` prefix (`AsyncCache`, `AsyncSession`, `AsyncUnitOfWork`, `AsyncCommandHandler`). Both live in the same file.

## When Modifying This Code

- If you change the validation model system, update `model_maker.py` and verify `test_base_validator.py`
- If you change the mutation system, update `base_guarded.py` (including `_wrap_public_methods`) and verify `test_base_guarded.py` + `test_make_immutable.py`
- If you change `__post_init__`, update `base_validator.py` (definition and trigger), and verify `test_post_init.py`
- If you change `reconstruct()`, update `reconstructable.py` and verify `test_post_init.py` + `test_base_validator.py`
- If you change domain classes, check `test_event_emitter.py`, `test_entity.py`, `test_value_object.py`
- If you change the type checks, update `type_handlers/extractors.py` and/or `type_handlers/checks` and verify tests
- If you change the bounded context logic, update `bounded_context.py` and check `test_bounded_context.py`
- If you change the projection layer, update `projection.py` (infrastructure/projection/) and verify `test_projection_classes.py`
- If you change the handler layer, update `handlers.py` and/or `base_handler.py` and verify `test_async_handlers.py`
- If you change `BaseOperation` field validation, update `base_operation.py` and verify `test_base_operation_port_check.py`
- If you change the application layer, update `port.py` and/or `use_case.py` and verify `test_port.py` / `test_use_case.py`
- If you change the UnitOfWork, update `unit_of_work.py` (sync + async) and verify `test_port.py` / `test_async_port.py` (includes `is_dirty` tests)
- If you change async counterparts (aggregated in `aod.application.async_` / `aod.infrastructure.async_`), update both sync and async test files
- If you change the container, update files in `container/` package (container.py, port_manager.py, session_manager.py, handler_manager.py, types.py) and verify `test_container.py`, `test_inject.py`, and container-related e2e tests
- Always add `__all__` to every `__init__.py` and `async_.py` to avoid `F401` lint warnings
- Always run `make check` before committing
- Event.emitted_at is the timestamp field.
- **No inline imports in tests** -- every import must be at the top of the file. Test-local classes are fine, but imports from `aod`, `pydantic`, `unittest`, `types`, etc. must be at module level.
- **`@field_validator` without `@classmethod`** -- Pydantic v2 field validators use `def name(cls, v)` without the `@classmethod` decorator. The `cls` parameter is passed automatically.
- **`@field_invariance` and `@invariance` also without `@classmethod`** -- Same rule applies.
- **No direct Pydantic imports** -- Never import `from pydantic import field_validator`. Use `from aod.domain.validation import field_invariance` instead, which wraps Pydantic's validator and raises `InvarianceException` on failure.

## Dependencies

- **Runtime**: `pydantic>=2.12.4`, `polyfactory>=3.3.0`, `typing-inspect>=0.9.0`
- **Dev**: `ruff`, `ty`, `pre-commit`, `pytest`, `pytest-cov`, `pytest-asyncio`
- **Build**: `setuptools`, `wheel`

## Test Count

1169 tests, 3 skipped (no `patch`/`mock.patch` in any test file)
97% code coverage (98/3656 lines missing)

## At the end of a task

Update docs, AGENTS.md and SKILL.md. Run `make check` to verify.

## No `patch` in tests

Zero `unittest.mock.patch` / `mock.patch` calls in tests. If a test needs `patch`, either:

1. **Test data is badly constructed** -- build real objects that trigger the code path (e.g., `def handle(self) -> User` for a handler with no Command param, `"NonExistentClass"` forward ref for unresolvable type hints)
2. **Implementation calls `get_type_hints` at runtime unnecessarily** -- but `get_handler` must use `get_type_hints` to resolve concrete session types (`MongoSession`, `PSQLSession`). This is correct -- no tests patch this path.

Guidelines:
- `inspect.signature` failure -> use a function with `__signature__` set to a non-Signature value via `setattr`
- `typing.get_type_hints` failure -> use an unresolvable forward reference string annotation (e.g., `x: "NonExistentClass"`)
- Handler without Command param -> override `handle` with `def handle(self) -> User` and suppress type checker with `# ty:ignore[invalid-method-override]`
- If a code path can only be triggered by patches, remove the test -- the defensive code is trivially correct
- **No inline imports in tests** -- every import must be at the top of the file. Test-local classes are fine, but imports from `aod`, `pydantic`, `unittest`, `types`, `inspect`, etc. must be at module level.
- **No fake `__model_fields__` workarounds** -- never create a fake class with a hand-crafted `__model_fields__` dict. Use real `BaseOperation`/`ProjectionBase` subclasses instead. If the code path you're testing is unreachable with real objects, remove both the dead code and the test.
- **Python 3.14 `issubclass` accepts Union** -- `issubclass(MySession, Session | None)` returns `True` in Python 3.14. No need to strip `None` before checking.
- **Python 3.14 `get_type_hints` doesn't raise** -- unlike older Python versions, `typing.get_type_hints` in Python 3.14 silently drops unresolvable forward references and returns `{}` instead of raising. A `try/except Exception: return {}` wrapper is dead code.
- **Python 3.14 `except` without parentheses (PEP 758)** -- `except ValueError, TypeError:` (no parens) is valid Python 3.14 and equivalent to `except (ValueError, TypeError):`. `ruff` strips the parens. Keep the form `ruff` produces.
