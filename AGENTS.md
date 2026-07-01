# attack-on-domain — Agent Guide

## Overview

`attack-on-domain` is a Python 3.14+ library providing Domain-Driven Design building blocks using Pydantic v2 under the hood. It implements entities, value objects, bounded contexts, domain events, and a validation system.

**Source code is under `code/`** — this directory is mapped as the package root in `pyproject.toml`.

## Workflow

The correct order for building a DDD system with this library:

### Step 1: Domain Layer

Create ValueObjects, Events, and the RootEntity that serves as the aggregate root. All other entities in the aggregate are nested inside the RootEntity's fields.

```python
from aod.domain import RootEntity, ValueObject, Field
from aod.events import Event

class OrderId(ValueObject):
    value: str

class OrderLine(ValueObject):
    product_id: str
    quantity: int = Field(ge=1)
    price: float = Field(ge=0)

class OrderPlaced(Event):
    order_id: str
    total: float

class Order(RootEntity):
    id: OrderId
    lines: list[OrderLine] = Field(default_factory=list)
    total: float = 0.0

    def add_line(self, product_id: str, quantity: int, price: float) -> None:
        line = OrderLine(product_id=product_id, quantity=quantity, price=price)
        self.lines.append(line)
        self.total += quantity * price
        self._event_emitter.emit(OrderPlaced(order_id=self.id.value, total=self.total))
```

### Step 2: Application Layer — UseCases, Commands/Queries, Handlers

Use Pydantic `BaseModel` for UseCase input, and Commands/Queries for handlers. **Commands and Queries are internal** — created by the UseCase, never by the user. `BaseModel` subclasses are the public contract for `run()`. Use `get_base_model(cls)` from `aod.domain.validation` to get a BaseModel from a domain class (Entity, RootEntity, ValueObject).

```python
from aod.application import UseCase, Command, Query, CommandPort, QueryPort
from pydantic import BaseModel

class PlaceOrderInput(BaseModel):
    order_id: str
    product_id: str
    quantity: int
    price: float

class PlaceOrder(Command[Order, None]):
    order_id: str
    product_id: str
    quantity: int
    price: float

class GetOrder(Query[Order, Order | None]):
    order_id: str

class PlaceOrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]
    get_order: QueryPort[GetOrder]

    def run(self, dto: PlaceOrderInput) -> None:
        order = Order(id=dto.order_id)
        order.add_line(dto.product_id, dto.quantity, dto.price)
        self.place_order.handle(PlaceOrder(
            order_id=dto.order_id,
            product_id=dto.product_id,
            quantity=dto.quantity,
            price=dto.price,
        ))
```

### Step 3: Infrastructure Layer — Implementations

Create the concrete Handler implementations and Sessions. Rename infrastructure handlers to avoid confusion with application protocols. Session IS the data access abstraction — no repositories or stores.

```python
from aod.infrastructure import CommandHandler as InfraCommandHandler, QueryHandler as InfraQueryHandler, Session
from aod.domain import PrivateField

# Create your Session subclass
class SqlSession(Session):
    _connection: object = PrivateField(default_factory=dict)

    def execute(self, operation: object) -> object:
        # Write operations
        ...

    def query(self, operation: object) -> object:
        # Read operations
        ...

    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def is_dirty(self) -> bool: return False

# Handlers use YOUR session type
class PlaceOrderHandler(InfraCommandPort[PlaceOrder]):
    session: SqlSession  # Concrete type — injected by container
    def handle(self, command: PlaceOrder) -> None:
        self.session.execute(...)

class GetOrderHandler(InfraQueryPort[GetOrder]):
    session: SqlSession  # Concrete type — injected by container
    def handle(self, query: GetOrder) -> Order | None:
        return self.session.query(...)
```

### Step 4: Container and Injection

Wire everything together with the AdapterContainer and inject dependencies.

```python
from aod.infrastructure import AdapterContainer

container = AdapterContainer(sessions={SqlSession}, handlers=[PlaceOrderHandler, GetOrderHandler])
place_order = container.adapt_use_case(PlaceOrderUseCase)
place_order.run(PlaceOrderInput(order_id="1", product_id="p1", quantity=2, price=9.99))
```

## Documentation Site

The documentation site is built with **zensical** (a mkdocs-material-compatible static site generator). Config is in `zensical.toml` at the project root. The style is FastAPI-like:

- **Fixed header** with navigation tabs (Getting Started, Domain, Application, Infrastructure, Testing, API Reference)
- **No left sidebar** — the sidebar only shows the Table of Contents for the current page (right side)
- Navigation uses `navigation.tabs` and `navigation.tabs.sticky` features
- Custom CSS in `docs/stylesheets/extra.css`
- Custom template override in `docs/overrides/main.html` (hides primary sidebar)

**Build command:** `uv run zensical build --clean`
**Output:** `site/` directory (gitignored)

## GitHub Pages

The docs deploy automatically via `.github/workflows/docs.yml`:

- **Trigger**: pushes to `master` touching `docs/`, `zensical.toml`, or the workflow file
- **Manual**: use `workflow_dispatch` from the Actions tab
- **Build**: `uv sync --group dev && uv run zensical build --clean`
- **Deploy**: `actions/upload-pages-artifact@v3` + `actions/deploy-pages@v4`
- **Setup**: enable "GitHub Actions" as the Pages source in repo Settings > Pages

## CQRS-First Documentation

All docs now use the CQRS pattern as the primary example. Key tenets:

- UseCases declare `CommandPort[Command]` and `QueryPort[Query]` fields, NOT custom repository ports
- Custom `Port` subclasses are only for non-database concerns (API clients, notifications, etc.)
- Infrastructure handlers (`CommandHandler[C]`, `QueryHandler[Q]`) implement the handler ports
- The container auto-wires handlers into UseCases via `container.adapt_use_case()`
- Updated pages: index.md, getting-started/*, application/*, domain/events.md

## Docs Structure

```
docs/
├── index.md                          # Home page with hero, features, architecture diagram
├── stylesheets/extra.css             # Custom CSS for FastAPI-like look
├── overrides/main.html               # Template override (hides left sidebar)
├── getting-started/
│   ├── installation.md               # pip/uv install, requirements, dependencies
│   ├── quickstart.md                 # 5-minute guide: VOs, Entities, Ports, UseCase, DI
│   └── concepts.md                   # DDD theory: VOs, Entities, Aggregates, Services, Events
├── domain/
│   ├── entities.md                   # Entity, RootEntity: constructors, mutation, reconstruct, post_init vs invariance
│   ├── entity-id.md                  # Identity Field: Field(id=True), hash caveat
│   ├── value-objects.md              # ValueObject: immutability, equality, validation, post_init vs invariance
│   ├── services.md                   # Service: stateless ops, event emission, type constraints
│   ├── events.md                     # Event: emission, collection, EventCollector, assertions
│   ├── bounded-context.md            # BoundedContext: constructor, discovery, type checks
│   └── validation.md                 # Validation: AfterValidator, field_invariance, invariance
├── application/
│   ├── use-cases.md                  # UseCase, AsyncUseCase: run(), auto-wired fields
│   ├── ports.md                      # Port, Logger, EventBus, UnitOfWork, Cache (sync + async)
│   ├── contracts.md                  # Command, Query: type params, field validation
│   └── handlers.md                   # CommandHandler, QueryHandler, async variants
├── infrastructure/
│   ├── sessions.md                   # Session, AsyncSession: transactions, dirty tracking
│   ├── projections.md                # ReadProjection, WriteProjection, async variants
│   └── container.md                  # AdapterContainer: sessions, handlers, ports, injection
├── schema/
│   └── index.md                      # Schema system overview, AutoDoc, consistency checks
├── testing/
│   └── index.md                      # build, events_of, assert_*, spy classes, FakeDomain
└── api/
    └── index.md                      # Full API reference for all public classes
```

## Writing Docs Conventions

1. **No emojis** in source files
2. **No comments** in code examples
3. **Python 3.14+ syntax** (type | None, etc.)
4. **Parameter-by-parameter docs** for every function/class constructor — use markdown tables
5. **Every page ends with "## Next Steps"** with bullet links to related pages
6. **Relative links only** (no `/absolute/paths`)
7. **Code blocks** use ```python
8. All links assume the Markdown file extension (.md) — zensical resolves them

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
│   │       │   ├── __init__.py        # Sync: LogEntry, SpyLogger, SpyEventBus, SpyUnitOfWork
│   │       │   └── async_/
│   │       │       └── __init__.py    # Async (plain name): SpyLogger, SpyEventBus, SpyUnitOfWork
│   └── _internal/                    # Private — not semver-stable
│       ├── core/                     # Framework internals
│       │   ├── async_utils.py        # should_await (sync/async bridge)
│       │   ├── base_validator.py     # ValidationModelMeta + BaseValidator
│       │   ├── reconstructable.py    # ReconstructMixin (reconstruct classmethod)
│       │   ├── base_sealed.py        # BaseSealed (always-blocked mutation)
│       │   ├── base_guarded/         # BaseGuarded, MutatingContext, make_immutable subsystem
│       │   ├── base_behaviour.py     # BaseBehaviour (allows mutation inside methods)
│       │   ├── base_operation.py     # BaseOperation(BaseBehaviour) — adds _event_emitter, events, logger, event_bus, cache
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
│       │   ├── cache/                # Cache port — sync + async
│       │   │   ├── __init__.py
│       │   │   └── cache.py           # Cache(Port) + AsyncCache(Port)
│       │   ├── contracts/            # Command, Query — application contracts
│       │   │   ├── __init__.py       # Command, Query
│       │   │   └── contracts.py      # Command(BaseSealed), Query(BaseSealed) with field validation
│       │   ├── event_bus/            # EventBus port — sync + async
│       │   │   ├── __init__.py
│       │   │   └── event_bus.py       # EventBus(Port) + AsyncEventBus(Port)
│       │   ├── logger/               # Logger port — sync + async
│       │   │   ├── __init__.py
│       │   │   └── logger.py          # Logger(Port) + AsyncLogger(Port)
│       │   ├── unit_of_work/         # UnitOfWork port — sync + async
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
│       └── testing/                  # Testing utilities (implementation)
│           ├── __init__.py           # Re-exports: DomainType, FakeDomain, build, helpers
│           ├── helpers.py            # build(), events_of(), assert_event_emitted(), etc.
│           ├── doubles/              # Spy implementations
│           │   ├── __init__.py       # Re-exports all (sync + async)
│           │   ├── async_/
│           │   │   └── __init__.py   # Re-exports async spies from application
│           │   └── application/
│           │       ├── __init__.py
│           │       ├── logger.py     # LogEntry, SpyLogger, AsyncSpyLogger
│           │       ├── event_bus.py  # SpyEventBus, AsyncSpyEventBus
│           │       └── unit_of_work.py  # SpyUnitOfWork, AsyncSpyUnitOfWork
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
BaseValidator (metaclass: ValidationModelMeta → ABCMeta)
└── BaseGuarded                     (mutation-guarded)
    ├── BaseBehaviour               (extends BaseGuarded — allows mutation inside methods)
    │   ├── BaseOperation           (adds _event_emitter, events, logger, event_bus, cache)
    │   │   ├── UseCase             → +uow, +run()
    │   │   ├── AsyncUseCase        → +uow, +async run()
    │   │   ├── ProjectionBase
    │   │   │   ├── ReadProjectionBase
    │   │   │   │   ├── ReadProjection       → +session, +read()
    │   │   │   │   └── AsyncReadProjection  → +async read()
    │   │   │   ├── WriteProjectionBase
    │   │   │   │   ├── WriteProjection      → +session, +write()
    │   │   │   │   └── AsyncWriteProjection → +async write()
    │   │   │   ├── Projection               → +read() +write()
    │   │   │   └── AsyncProjection          → +async read() +write()
    │   │   └── Service (in domain, does NOT inherit BaseOperation — just BaseBehaviour)
    │   └── BaseSealed              (always blocks mutation)
    │       ├── ValueObject(ReconstructMixin, BaseSealed) → has reconstruct ✓
    │       ├── Event
    │       ├── Command
    │       └── Query
    └── BaseGuarded (direct inheritance for Port, Session, etc.)
```

Use `pydantic.BaseModel` directly for DTOs. Use `get_base_model(cls)` from `aod.domain.validation` to get a constrained BaseModel from a domain class.

`ReconstructMixin` is only mixed into `Entity` and `ValueObject`. `Service` and `UseCase` never see `reconstruct()`.

## Key Architectural Decisions

### Single Metaclass: `ValidationModelMeta`
Only one metaclass exists in the framework — `ValidationModelMeta` on `BaseValidator`. It generates the two Pydantic models (`__validation_model__` and `__raw_model__`) at class creation time. It inherits from `ABCMeta` so that `@abstractmethod` is enforced for classes like `UseCase`.

The old `GuardedBaseMeta` and `EntityMeta` metaclasses were eliminated:
- **Method wrapping** lives in `BaseGuarded.__init_subclass__` which calls `_wrap_public_methods(cls)`
- **Root entity flag** uses `issubclass(cls, RootEntity)` — no flag variable needed
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

### `Entity.can_mutate()` — Public Mutation Guard

`Entity` exposes a public `can_mutate()` method that controls whether the entity can be mutated. It delegates to `_can_mutate()` (the internal hook used by `BaseGuarded._is_mutation_allowed`):

```python
class Entity(ReconstructMixin, BaseGuarded):
    @inherit_context
    def _can_mutate(self) -> bool:
        return self.can_mutate()

    def can_mutate(self) -> bool:
        return True
```

- **Default**: returns `True` — mutation allowed inside public methods, blocked from outside.
- **Override**: subclasses override `can_mutate()` to return `False` or a dynamic condition:
  ```python
  class User(RootEntity):
      id: UserId = Field(id=True)
      _locked: bool = PrivateField(default=False)

      def can_mutate(self) -> bool:
          return not self._locked
  ```
- When `can_mutate()` returns `False`, any mutation attempt raises `MutationForbiddenException`.
- Only `Entity` and its subclasses (`RootEntity`) have this hook. `ValueObject` and `BaseSealed` always block mutation.

#### `@mutable` decorator

The `@mutable` decorator (exposed as `from aod.domain.validation import mutable`) marks a method to inherit the mutation context from its caller, bypassing the `can_mutate()` guard. Previously called `inherit_context` (still used internally in the framework). This is needed for methods like `lock()`/`unlock()` that must mutate even when the entity is locked:

```python
from aod.domain.validation import mutable

class User(RootEntity):
    id: UserId = Field(id=True)
    _locked: bool = PrivateField(default=False)

    def can_mutate(self) -> bool:
        return not self._locked

    @mutable
    def lock(self) -> None:
        self._locked = True

    @mutable
    def unlock(self) -> None:
        self._locked = False
```

Without `@mutable`, `unlock()` would raise `MutationForbiddenException` because the entity is locked and `can_mutate()` returns `False`.

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
    id: UserId = Field(id=True)
    name: str

    def __post_init__(self):
        self._event_emitter.emit(UserCreatedEvent(user_id=self.id.value))
        self.setup_defaults()

    def setup_defaults(self):
        # public method — works because __mutating_context__ exists
        ...
```

Works for `Entity`, `RootEntity`, `ValueObject`, `Service` (all inherit from `BaseGuarded`). Also works for `UseCase` and any `BaseValidator` subclass.

### `__post_init__` vs `@invariance` / `@field_invariance`

Both run at construction time but serve different purposes:

| Concern | `__post_init__` | `@invariance` / `@field_invariance` |
|---------|-----------------|--------------------------------------|
| What it does | Post-construction logic using the instantiated instance (`self`) | Validates field or model values before they are stored |
| Use case | Emit creation events, compute derived values, call setup methods | Check business rules: "quantity must be positive", "end must be after start" |
| Runs on `reconstruct()` | **No** | **No** |
| Has `self` | Yes | No (receives `cls` and raw value) |
| Can mutate fields | Yes (during the hook) | No |

Do NOT override `__init__` — use `__post_init__` instead. See `docs/domain/entities.md` for detailed guidance.

### Identity Field

Every `Entity` / `RootEntity` subclass must have exactly one identity field, marked with `Field(id=True)`. The identity field can be any type — `int`, `str`, `UUID`, or a `ValueObject` subclass:

```python
class UserId(ValueObject):
    value: str

class User(RootEntity):
    id: UserId = Field(id=True)
    name: str
    father: int  # reference to another User, not the identity
```

This allows entities with multiple fields of the same type, where only one is the identity.

`Entity.__init_subclass__` enforces this at class creation time:
- Zero fields with `Field(id=True)` → `NoIdentityFieldException`
- Multiple fields with `Field(id=True)` → `TooManyIdentityFieldsException`

Since entities use their identity field for hashing, **mutating an entity's ID changes its hash**, which can cause issues if the entity is stored in a `set` or used as a `dict` key. Avoid mutating entity identities after construction. See `docs/domain/entity-id.md`.

### Equality Behavior

- **ValueObject**: compared by all public fields (`==` compares every annotated field; `PrivateField` attributes are excluded). Two VOs with identical public field values are equal.
- **Entity / RootEntity**: compared only by their identity field. Two entities with the same identity value are equal regardless of other field values.

### Type Checking System (`type_handlers/`)
Three check functions enforce DDD type constraints at `BoundedContext` construction:

#### `check_entity(entity_cls)` / `check_root_entity(entity_cls)`
Raises `InvalidNestedTypeError` if any field references `RootEntity` (or any subclass of it).

#### `check_value_object(vo_cls)`
Raises `InvalidNestedTypeError` if any field references `Entity` **or** `RootEntity` (ValueObjects must only contain primitives or other ValueObjects). Additionally, ValueObject raises `InvalidValueObjectFieldError` at class creation if any field is marked with `Field(id=True)` — ValueObjects are identity-less by design.

#### `check_service(service_cls)`
Iterates all public methods via `inspect.getmembers`. For each method:
- Inspects parameters and return type via `inspect.signature`
- Resolves forward references via `typing.get_type_hints`
- Raises `InvalidServiceParameterError` if any param or return type is a non-root `Entity`

**Allowed in services**: custom classes, `RootEntity`, `ValueObject`
**Forbidden in services**: non-root `Entity`

### BoundedContext Constructor

Use in the **entry point** of your app (container), not in `domain/__init__.py`.

```python
class BoundedContext:
    def __init__(
        self,
        aggregate_roots: Iterable[RootEntityType] | None = None,
        services: Iterable[ServiceType] | None = None,
        *,
        name: str | None = None,
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
- `InfrastructureException` — base for infrastructure layer errors

**`DomainException` subclasses:**
- `MutationForbiddenException(DomainException)` — mutation outside allowed context
- `InvarianceException(DomainException, ValueError)` — field/model invariance violated
- `InvalidCommandFieldTypeError` — Command/Query field references non-root Entity
- `InvalidValueObjectFieldError` — a `ValueObject` has a field marked with `Field(id=True)`, which is not allowed
- `InvalidQueryResultTypeError` — `Query` TResult does not include a `RootEntity`
- `InvalidGenericTypeArgError` — generic argument fails its constraint
- `InvalidEntityTypeError` — not an `Entity` subclass
- `InvalidRootEntityTypeError` — `Entity` but not `RootEntity`
- `InvalidServiceTypeError` — not a `Service` subclass
- `ClassExpectedError` — instance given where class required
- `InvalidNestedTypeError` — Entity field references forbidden domain type
- `InvalidServiceParameterError` — Service method parameter has disallowed type
- `DuplicateDomainTypeError` — domain type registered in >1 `BoundedContext`
- `ModelValidationError` — Pydantic validation failed during model construction (wraps `ValidationError`; if the cause is an `InvarianceException`, that is re-raised directly)

**`ApplicationException` subclasses:**
- `UnresolvableEntityError` — cannot determine `RootEntity` from Command/Query
- `CommitOutsideUnitOfWorkError` — commit attempted outside a `UnitOfWork` context
- `InvalidUseCasePortFieldError` — UseCase field is not a `Port` subclass (renamed from `InvalidPortFieldError` in the application layer)
- `InvalidHandlerPortFieldError` — `HandlerProtocol` port on a UseCase is missing its generic type argument

**`InfrastructureException` subclasses:**
- `HandlerResultTypeError` — handler returned wrong type
- `HandlerModelError` — handler class is missing a required field
- `PortNotFoundError` — no port of the requested type is registered on the container
- `SessionNotFoundError` — no session of the requested type is registered on the container
- `InvalidPortFieldError` — a field on an `AdapterContainer` subclass is not a Port type

> For details on when each is raised, see `docs/core/exceptions.md`.

### Public/Private Layer Separation

The package splits into two layers:

- **`aod.domain`, `aod.domain.validation`, `aod.exceptions`, `aod.application`, `aod.infrastructure`** — public API. These are thin re-export shims that surface symbols from `_internal`. User code and downstream tools must import from here.
- **`aod.application.async_`**, **`aod.infrastructure.async_`** — aggregated async counterparts. Import the same names as sync (e.g. `from aod.application.async_ import Cache` for `AsyncCache`).
- **`aod._internal.core`, `aod._internal.domain`, `aod._internal.application`, `aod._internal.infrastructure`** — private implementation. This is where everything is built and where new code goes. Not part of the supported public API and not semver-stable.

Public modules re-export from `_internal`; they contain no logic of their own. The reverse direction is never used — `_internal` never imports from `aod.domain` to avoid circular dependencies.

### `UseCase` Base Class

`UseCase` (public via `aod.application`) is the base for application-layer use cases. It extends `BaseOperation` (no `ReconstructMixin`) and provides a single abstract public method `run()` that subclasses must implement.

- **Fields are Handlers and Ports only** — UseCase fields must be `CommandHandler`, `QueryHandler`, or `Port` subclasses. Values are passed as parameters to `run()`, not declared as fields.
- **Blocked field types** — `Session` and `AsyncSession` are rejected via `__not_allowed_port_types__`. UseCases should NOT depend on sessions directly; use handlers instead.
- **Database access through Handlers** — UseCases communicate with the database ONLY through `CommandPort[Command]` and `QueryPort[Query]`. Do NOT create repository ports or custom ports for database access. The handlers are injected automatically by the container.
- **`run()` signature** — `run()` receives values as parameters. The wrapper passes `*args, **kwargs` through to the original method.
- The class has **no public methods** other than `run`; subclasses may add private helpers
- `_event_emitter` is a `PrivateField(default_factory=EventEmitter)`, ready for direct event emission
- Auto-wired fields with Null Object defaults (no `is not None` checks):
  - `uow: UnitOfWork` — auto-commits on success (only if `is_dirty`), auto-rollbacks on failure; defaults to `_NullUnitOfWork` (no-op)
  - `logger: Logger` — auto-logs completion (with event count) and failure; defaults to `_NullLogger` (no-op)
  - `event_bus: EventBus` — auto-publishes collected events after successful commit; defaults to `_NullEventBus` (no-op)
  - `cache: Cache` — auto-flushed after successful commit; defaults to `_NullCache` (no-op)

- `__init_subclass__` automatically wraps any subclass's `run` to:
  1. Open an `EventCollector` context
  2. Invoke the original `run` body
  3. Replace `self.events` with the list of captured events
- Subclasses access the events collected during the last `run` via `self.events` (public `Field(default_factory=list, init=False)`)

Events emitted directly by the UseCase via `self._event_emitter.emit(...)` or by any entity touched during `run` are all captured and stored on the UseCase, replacing any events from previous runs.

**Field validation**: UseCase fields are validated at class creation by `BaseOperation.__init_subclass__`. Only `Port` subclasses are allowed as fields. Infrastructure handlers (`BaseHandler`, `AsyncBaseHandler`) and `Session`/`AsyncSession` are rejected. Application-layer generic handlers (`AppCommandHandler[T]`, `AppQueryHandler[T]`) are accepted since they inherit from `HandlerProtocol(Port)`. Non-Port fields (primitives, custom classes) raise `InvalidUseCasePortFieldError`.

```python
# Correct: Ports as fields, values in run()
class CreateUser(UseCase):
    user_client: UserRestClient  # Port dependency

    def run(self, user_id: int, name: str) -> None:
        user = User(id=user_id, name=name)
        self.user_client.save(user)

# Wrong: values as fields
class CreateUser(UseCase):
    user_id: int  # InvalidUseCasePortFieldError!
    name: str     # InvalidUseCasePortFieldError!
```

**Infrastructure handler inheritance**: Infrastructure `CommandHandler`/`QueryHandler` types inherit from both `BaseHandler` and the application-layer `HandlerProtocol` (`Port`). This satisfies Pydantic `isinstance` checks when handlers are used in any context requiring the app-layer type.

**Container sessions**: `AdapterContainer.sessions` holds session **classes** (`type[Session] | type[AsyncSession]`), not instances. `get_session(session_cls)` instantiates the matching class, tracks the instance in `_sessions_needed`, and returns it. `get_uow()` checks session types and creates `UnitOfWork`/`AsyncUnitOfWork` with the needed instances.

### `Port` Base Class

`Port` (public via `aod.application`) is an abstract base class for defining dependency interfaces (ports/gateways) in the application layer. It extends `BaseGuarded`, so:
- Concrete subclasses' public methods are auto-wrapped with mutation context (can mutate fields)
- Mutations are blocked from outside
- Supports `@abstractmethod` (skipped by `_wrap_public_methods`)
- Subclasses declare fields and abstract methods that infrastructure will implement

Built-in port types (all `aod.application`):
- **`Logger`** / **`AsyncLogger`** — `debug(msg, **context)`, `info(msg, **context)`, `warning(msg, **context)`, `error(msg, **context)`
- **`EventBus`** / **`AsyncEventBus`** — `publish(*events)` for publishing domain events
- **`UnitOfWork`** / **`AsyncUnitOfWork`** — `commit()`, `rollback()`, `begin()` for transactional boundaries
- **`Cache`** / **`AsyncCache`** — `get(key)`, `set(key, value, ttl=None)`, `delete(key)`, `flush()`, `set_promise()`, `delete_promise()`

Infrastructure implementations of these ports inherit from both `BaseGuarded` and the application `Port` type.

### `HandlerProtocol`

All application-layer handler types (`CommandHandler`, `QueryHandler`, `AsyncCommandHandler`, `AsyncQueryHandler`) inherit from `HandlerProtocol(Port)`. Infrastructure handler types inherit from both `BaseHandler` (mutation-guarded behaviour) and the corresponding app-layer `HandlerProtocol`.

**Runtime type checking**: `HandlerProtocol.__init_subclass__` wraps `handle()` with a type checker that verifies the command/query passed to `handle()` matches the generic type parameter. If not, raises `TypeError`.

```python
class CreatePetHandler(CommandHandler[CreatePet]):
    def handle(self, command: CreatePet) -> None: ...

handler = CreatePetHandler()
handler.handle(CreatePet(...))  # OK
handler.handle(OtherCommand(...))  # TypeError: Expected CreatePet, got OtherCommand
```

### Contracts (`Command` / `Query`)

`aod.application` provides application-layer contracts:

- **`Command[TEntity, TResult]`** / **`Query[TEntity, TResult]`** — immutable data classes for writes/reads (extend `BaseSealed`, validate `TEntity` is `RootEntity` subclass at class creation). Field types are checked at `__init_subclass__` — any field referencing a non-root `Entity` (even nested in generics like `list[Entity]`) raises `DomainException`. `Query` additionally requires its `TResult` type argument to contain at least one `RootEntity` (e.g. `Query[User, User]`, `Query[User, list[User]]`, `Query[User, tuple[int, User | None]]` are all valid).

Contract validation lives in `aod._internal.application.contracts.contracts.py` as private helpers `_validate_fields_no_entity` and `_validate_result_contains_root_entity`, called from `Command.__init_subclass__` and `Query.__init_subclass__` respectively.

### CommandHandler / QueryHandler

`aod.infrastructure` provides abstract handler bases with automatic result-type checking:

- **`CommandHandler[C]`** / **`QueryHandler[Q]`** — abstract bases with `handle(self, command: TCommand) -> object` method
- **`AsyncCommandHandler[C]`** / **`AsyncQueryHandler[Q]`** — async variants with `async handle(self, command: TCommand) -> object`
- **`BaseHandler`** — base class with `_wrap_handle()` that validates the `handle()` return type against the handler's generic parameter at runtime. Uses `get_last_generic_arg` from `generic_utils.py`.

**Runtime type checking**: `HandlerProtocol.__init_subclass__` wraps `handle()` with a type checker that verifies the command/query passed to `handle()` matches the generic type parameter. If not, raises `TypeError`.

```python
class CreatePetHandler(CommandHandler[CreatePet]):
    def handle(self, command: CreatePet) -> None: ...

handler = CreatePetHandler()
handler.handle(CreatePet(...))  # OK
handler.handle(OtherCommand(...))  # TypeError: Expected CreatePet, got OtherCommand
```

Zero `# type: ignore` in `handlers.py`.

### Projection System (`aod.infrastructure.projection`)

The projection system provides read and write projections with automatic event collection, logging, and event bus publishing. It is isolated from the Command/Query dispatch system.

#### Data Models

- **`ReadModel(BaseSealed)`** — immutable data class for read projection inputs. Fields can reference any type.
- **`WriteModel(BaseSealed)`** — immutable data class for write projection inputs. Fields can reference any type.

#### Base Classes

- **`ProjectionBase(BaseOperation)`** — inherits `_event_emitter`, `events`, `logger`, `event_bus`, `cache` from `BaseOperation`. Fields must be `Port` subclasses. `HandlerProtocol` and its subclasses are rejected via `__not_allowed_port_types__ = (HandlerProtocol,)`. At most one `Session` field is allowed (validated separately).
- **`ReadProjectionBase(ProjectionBase)`** — wraps `read()` with `EventCollector` + log + event_bus publish.
- **`WriteProjectionBase(ProjectionBase)`** — wraps `write()` with `CommitContext` + `EventCollector` + log + rollback + event_bus publish.

```python
# Correct: Port fields, max one Session
class UserProjection(ReadProjection):
    user_client: UserRestClient  # Port dependency
    session: Session | None = None  # Optional session

    def read(self, model: ReadModel) -> list[User]:
        return self.user_client.find_all()

# Wrong: Handler field
class BadProjection(ReadProjection):
    handler: CommandHandler[SaveUser]  # InvalidUseCasePortFieldError!

# Wrong: Multiple sessions
class BadProjection(ReadProjection):
    session: Session | None = None
    other_session: AsyncSession | None = None  # InvalidPortFieldError!
```

#### Concrete Classes

- **`ReadProjection(ReadProjectionBase)`** — `session: Session | None`, abstract `read(model: ReadModel)`.
- **`WriteProjection(WriteProjectionBase)`** — `session: Session | None`, abstract `write(model: WriteModel)`.
- **`Projection(ReadProjection, WriteProjection)`** — both `read()` and `write()` methods.

#### Async Counterparts

- **`AsyncReadProjection`** — async `read()`, uses `should_await` on logger/event_bus/session calls.
- **`AsyncWriteProjection`** — async `write()`, uses `should_await` on logger/event_bus/session calls.
- **`AsyncProjection`** — both async `read()` and `write()`.

Projections exist independently and are never mixed with `Command`/`Query`, `UnitOfWork`, or `Repository`.

### Test Doubles (`aod._internal.testing.doubles`)

Spy classes for testing application-layer ports, organized under `aod/_internal/testing/doubles/`:

```
aod/_internal/testing/
├── __init__.py                     # Re-exports all spies
├── helpers.py                      # build(), events_of(), assert_event_emitted()
├── doubles/
│   ├── __init__.py                 # Re-exports all (sync + async)
│   ├── async_/__init__.py          # Async spy re-exports
│   ├── application/
│   │   ├── __init__.py
│   │   ├── cache.py                # SpyCache, AsyncSpyCache
│   │   ├── logger.py               # LogEntry, SpyLogger, AsyncSpyLogger
│   │   ├── event_bus.py            # SpyEventBus, AsyncSpyEventBus
│   │   └── unit_of_work.py         # SpyUnitOfWork, AsyncSpyUnitOfWork
│   └── infrastructure/
│       ├── __init__.py
│       └── session.py              # SpySession, SpyAsyncSession
└── faker/
    ├── __init__.py
    └── faker.py                    # DomainType, FakeDomain
```

Public re-exports live at `aod/testing/`:
- `from aod.testing import FakeDomain, build, events_of, assert_event_emitted, assert_no_events, check_invariant`
- `from aod.testing.doubles import SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache, SpySession, SpyAsyncSession` (sync)
- `from aod.testing.doubles.application.async_ import SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache` (async variants, plain names)

### Testing Utilities (`aod.testing`)

| Import | What |
|--------|------|
| `from aod.testing import FakeDomain` | Factory for domain objects with auto-generated fake data |
| `from aod.testing import build` | Construct domain objects skipping validation |
| `from aod.testing import events_of` | Extract events emitted by an entity/service/vo |
| `from aod.testing import assert_event_emitted, assert_no_events` | Event assertions |
| `from aod.testing import check_invariant` | Run a single invariant validator |
| `from aod.testing.doubles import SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache, SpySession, SpyAsyncSession` | Sync test doubles |
| `from aod.testing.doubles.application.async_ import SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache` | Async test doubles (same names) |

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
- If you change the container, update `container.py` and verify `test_container.py`, `test_inject.py`, and container-related e2e tests
- Always add `__all__` to every `__init__.py` and `async_.py` to avoid `F401` lint warnings
- Always run all tests before committing
- `Event.emitted_at` is the timestamp field.
- **No inline imports in tests** — every import must be at the top of the file. Test-local classes are fine, but imports from `aod`, `pydantic`, `unittest`, `types`, etc. must be at module level.
- **`@field_validator` without `@classmethod`** — Pydantic v2 field validators use `def name(cls, v)` without the `@classmethod` decorator. The `cls` parameter is passed automatically.
- **`@field_invariance` and `@invariance` also without `@classmethod`** — Same rule applies: `@classmethod` is never used in decorator stacks.
- **No direct Pydantic imports** — Never import `from pydantic import field_validator`. Use `from aod.domain.validation import field_invariance` instead, which wraps Pydantic's validator and raises `InvarianceException` on failure.

## Dependencies

- **Runtime**: `pydantic>=2.12.4`, `polyfactory>=3.3.0`, `typing-inspect>=0.9.0`
- **Dev**: `ruff`, `ty`, `pre-commit`, `pytest`, `pytest-cov`, `pytest-asyncio`
- **Build**: `setuptools`, `wheel`

## Test Count

1146 tests (no `patch`/`mock.patch` in any test file)

## At the end of a task

Update docs, AGENTS.md and the SKILLS.md

## No `patch` in tests

Zero `unittest.mock.patch` / `mock.patch` calls in tests. If a test needs `patch`, either:

1. **Test data is badly constructed** — build real objects that trigger the code path (e.g., `def handle(self) -> User` for a handler with no Command param, `"NonExistentClass"` forward ref for unresolvable type hints)
2. **Implementation calls `get_type_hints` at runtime unnecessarily** — but `get_handler` must use `get_type_hints` to resolve concrete session types (`MongoSession`, `PSQLSession`). This is correct — no tests patch this path.

Guidelines:
- `inspect.signature` failure → use a function with `__signature__` set to a non-Signature value via `setattr`
- `typing.get_type_hints` failure → use an unresolvable forward reference string annotation (e.g., `x: "NonExistentClass"`)
- Handler without Command param → override `handle` with `def handle(self) -> User` and suppress type checker with `# ty:ignore[invalid-method-override]`
- If a code path can only be triggered by patches, remove the test — the defensive code is trivially correct
- **No inline imports in tests** — every import must be at the top of the file. Test-local classes are fine, but imports from `aod`, `pydantic`, `unittest`, `types`, `inspect`, etc. must be at module level.
- **No fake `__model_fields__` workarounds** — never create a fake class with a hand-crafted `__model_fields__` dict. Use real `BaseOperation`/`ProjectionBase` subclasses instead. If the code path you're testing is unreachable with real objects, remove both the dead code and the test.
- **Python 3.14 `issubclass` accepts Union** — `issubclass(MySession, Session | None)` returns `True` in Python 3.14. No need to strip `None` before checking.
- **Python 3.14 `get_type_hints` doesn't raise** — unlike older Python versions, `typing.get_type_hints` in Python 3.14 silently drops unresolvable forward references and returns `{}` instead of raising. A `try/except Exception: return {}` wrapper is dead code.
- **Python 3.14 `except` without parentheses (PEP 758)** — `except ValueError, TypeError:` (no parens) is valid Python 3.14 and equivalent to `except (ValueError, TypeError):`. `ruff` strips the parens. Keep the form `ruff` produces.
