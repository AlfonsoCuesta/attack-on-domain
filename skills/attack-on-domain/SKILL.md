---
name: attack-on-domain
description: "Use ONLY when the user is building a Domain-Driven Design system with this library. Covers entities, value objects, bounded contexts, domain events, the dual-model Pydantic validation system."
---

# attack-on-domain — Domain-Driven Design Library

Python 3.14+ DDD building blocks with Pydantic v2 under the hood.

Source code is under `code/` (mapped as package root in `pyproject.toml`).

## Public API

| Import | What |
|--------|------|
| `from aod.domain import BoundedContext, Entity, RootEntity, ValueObject, Service` | Domain primitives |
| `from aod.domain import Field, PrivateField` | Field wrappers |
| `from aod.events import Event` | Event base class |
| `from aod.events import EventCollector` | Cross-aggregate event capture |
| `from aod.domain.validation import field_invariance, invariance, inherit_context` | Validation decorators |
| `from aod.domain.validation import AfterValidator, BeforeValidator` | Pydantic validators |
| `from aod.domain import DomainException` | Domain base exception |
| `from aod.domain.exceptions import MutationForbiddenException, InvalidEntityTypeError, InvarianceException, ModelValidationError, …` | Domain-specific exceptions |
| `from aod.application import ApplicationException` | Application base exception |
| `from aod.application.exceptions import UnresolvableEntityError, CommitOutsideUnitOfWorkError, InvalidUseCasePortFieldError` | Application-specific exceptions |
| `from aod.infrastructure import InfrastructureException` | Infrastructure base exception |
| `from aod.infrastructure.exceptions import DuplicateHandlerError, HandlerNotFoundError, HandlerResultTypeError, HandlerModelError, PortNotFoundError, SessionNotFoundError, InvalidPortFieldError` | Infrastructure-specific exceptions |

| `from aod.application import UseCase` | UseCase base class |
| `from aod.application import Port` | Abstract port/gateway base class |
| `from aod.application import Logger, EventBus, UnitOfWork, Cache` | Built-in port types (sync) |
| `from aod.application.async_ import Cache, EventBus, Logger, UnitOfWork` | Async versions (methods are coroutines) |
| `from aod.application import Command, Query` | Application contracts |
| `from aod.infrastructure import CommandHandler, QueryHandler` | Infrastructure handlers |
| `from aod.infrastructure import ReadProjection, WriteProjection, Projection` | Projection base classes |
| `from aod.infrastructure import AsyncReadProjection, AsyncWriteProjection, AsyncProjection` | Async projection classes |
| `from aod.infrastructure import ReadModel, WriteModel` | Projection data models |
| `from aod.infrastructure import inject_adapters` | Dependency injection for UseCases and Projections |

## Testing Utilities

| Import | What |
|--------|------|
| `from aod.testing import FakeDomain` | Factory for domain objects with auto-generated fake data |
| `from aod.testing import build` | Construct domain objects skipping validation (raw model) |
| `from aod.testing import events_of` | Extract events emitted by an entity/service/vo |
| `from aod.testing import assert_event_emitted, assert_no_events` | Event assertions |
| `from aod.testing import check_invariant` | Run a single invariant validator |
| `from aod.testing.doubles.application import LogEntry, SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache` | Sync test doubles |
| `from aod.testing.doubles import SpySession, SpyAsyncSession` | Session test doubles |
| `from aod.testing.doubles.application.async_ import SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache` | Async test doubles (plain names) |

## Domain Primitives

### ValueObject
- **Immutable** — inherits `BaseSealed`, blocks all mutation (`__setattr__`, `__delattr__`, etc.)
- For identity-less values: money, addresses, quantities

### Entity
- **Mutable** — inherits `BaseGuarded`, auto-wraps public methods with mutation context
- Has identity (typically an `id` field)
- Mutation blocked outside public methods; reads return immutable proxies

### RootEntity
- `class MyRoot(RootEntity):` — subclass of `Entity`, detected via `issubclass(cls, RootEntity)`
- Cannot be nested inside other entities (enforced at `BoundedContext` construction)

### Service
- **Behaviour** — inherits `BaseBehaviour`, allows mutation inside public methods
- `_event_emitter` via `PrivateField(default_factory=EventEmitter)`, same as Entity/ValueObject
- Methods must not accept or return non-root `Entity` types (enforced at `BoundedContext` construction)
- Mutation blocked from outside (reads return immutable proxies)

### UseCase
- `UseCase` is the base for application-layer use cases, available at `from aod.application import UseCase`
- Extends `BaseOperation` (which extends `BaseBehaviour`) — mutation allowed inside methods
- Declares `_event_emitter` as `PrivateField(default_factory=EventEmitter)` for direct event emission
- Declares `events: list[Event] = Field(default_factory=list, init=False)` for collected events
- Auto-wired fields with Null Object defaults (no `is not None` checks):
  - `uow: UnitOfWork` — commits on success, rolls back on failure; defaults to `_NullUnitOfWork` (no-op)
  - `logger: Logger` — auto-logs completion (with event count) and failure; defaults to `_NullLogger` (no-op)
  - `event_bus: EventBus` — auto-publishes collected events after successful commit; defaults to `_NullEventBus` (no-op)
  - `cache: Cache` — auto-flushed after successful commit; defaults to `_NullCache` (no-op)
- `run()` is abstract
- `__init_subclass__` auto-wraps `run()` with an `EventCollector` and captures events into `self.events`
- Events emitted via `self._event_emitter.emit(...)` inside `run()` are automatically collected in `self.events`
- UseCase fields are validated at class creation — infra handler fields (`BaseHandler`/`AsyncBaseHandler` subclasses) raise `InvalidUseCasePortFieldError`. Application-layer handlers (`AppCommandHandler[T]`, `AppQueryHandler[T]`), Port subclasses, and non-Port fields (primitives, custom classes) are accepted.
- Works with inheritance chains (UseCase → Abstract → Concrete)

### AsyncUseCase
- Same as UseCase but async: `uow: UnitOfWork | AsyncUnitOfWork`, `async run()`
- Uses `should_await` for logger/event_bus/cache calls

### Projection System
- Available at `from aod.infrastructure import ReadProjection, WriteProjection, Projection`
- Also async variants: `from aod.infrastructure import AsyncReadProjection, AsyncWriteProjection, AsyncProjection`
- **ReadModel(BaseSealed)** / **WriteModel(BaseSealed)** — data models for projection inputs
- **ProjectionBase(BaseOperation)** — base with `_event_emitter`, `events`, `logger`, `event_bus`, `cache`
- **ReadProjection** — `session: Session | None`, abstract `read(model: ReadModel)`. Auto-wraps with EventCollector + log + event_bus publish
- **WriteProjection** — `session: Session | None`, abstract `write(model: WriteModel)`. Auto-wraps with CommitContext + EventCollector + log + rollback + event_bus publish
- **Projection** — both `read()` and `write()` methods

### inject_adapters
- `from aod.infrastructure import inject_adapters`
- Unified injection for UseCase, AsyncUseCase, and Projection classes
- Auto-detects type and injects: `uow` (UseCase), `session` (Projection), plus `logger`, `event_bus`, `cache`
- Supports `**overrides` for custom values
- For UseCase also injects user-defined Ports and Handlers from the container

### Port
- `Port` is the base for defining dependency interfaces (ports/gateways), available at `from aod.application import Port`
- Extends `BaseGuarded` — mutable from inside public methods
- Supports `@abstractmethod` (these are skipped by `_wrap_public_methods`, so concrete subclasses must provide implementations)
- Subclasses declare fields and abstract methods; infrastructure provides concrete implementations
- Concrete public methods are auto-wrapped with mutation context (PASS state)

Built-in port types (all `aod.application`):
- **`Logger`** — `debug(msg, **context)`, `info(msg, **context)`, `warning(msg, **context)`, `error(msg, **context)`
- **`EventBus`** — `publish(*events)` for publishing domain events to external handlers
- **`UnitOfWork`** — `commit()`, `rollback()`, `begin()` for transactional boundaries (sync); `AsyncUnitOfWork` for async
- **`Cache`** — `get(key)`, `set(key, value, ttl=None)`, `delete(key)`, `flush()`, `set_promise()`, `delete_promise()` for caching (sync); `AsyncCache` for async (application-level `Cache` inherits from `Port`; infrastructure provides `Cache(Port)` with promise/flush support)
- **`Session`** — database abstraction (`execute`, `query`, `begin`, `commit`, `rollback`, `close`) — defined in `aod._internal.infrastructure.session`, not exported from `aod.application`

```python
from aod.application import Port, UseCase

class EmailGateway(Port):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None: ...

class SendEmailUseCase(UseCase):
    email: EmailGateway

    def run(self) -> None:
        self.email.send("user@example.com", "Hello", "World")
```

### Contracts

Application-layer contracts at `from aod.application import Command, Query`:

- **`Command[TEntity, TResult]`** / **`Query[TEntity, TResult]`** — immutable data classes for writes/reads; validate `TEntity` is a `RootEntity` subclass. Fields are checked — non-root `Entity` types are forbidden (including nested types like `list[Entity]`). `Query` additionally requires `TResult` to contain a `RootEntity` (e.g. `Query[User, tuple[int, User | None]]` is valid, `Query[User, int]` is not)

### CommandHandler / QueryHandler

Abstract handler bases at `from aod.infrastructure import CommandHandler, QueryHandler`:

- **`CommandHandler[C]`** / **`QueryHandler[Q]`** — abstract bases with `handle(command: TCommand) -> object` method; generic type is the specific Command/Query subclass
- **`AsyncCommandHandler[C]`** / **`AsyncQueryHandler[Q]`** — async variants with `async handle(command: TCommand) -> object`

Handler type validation uses `get_last_generic_arg` from `type_handlers/generic_utils.py` — works in any scope, avoids `NameError` with locally-defined handlers.

## Dual-Model Validation

Each user class gets **two** Pydantic models at class creation:
- `__validation_model__` — includes all field constraints, `@field_invariance` validators, `@invariance` model validators
- `__raw_model__` — strips all validators

`__init__` uses the validation model. `ReconstructMixin.reconstruct()` uses the raw model (bypasses re-validation). Only classes that mix in `ReconstructMixin` (`Entity`, `ValueObject`, `RootEntity`) have `reconstruct()` — `Service` and `UseCase` do not.

If Pydantic raises `ValidationError` during `__init__`, it is caught and:
- If the underlying cause is an `InvarianceException`, that exception is re-raised directly
- Otherwise, a `ModelValidationError(DomainException)` is raised wrapping the original error

## Validation Decorators

```python
from aod.domain.validation import field_invariance, invariance

class Money(ValueObject):
    amount: float
    currency: str

    @field_invariance("amount")
    @classmethod
    def _amount_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("amount must be positive")
        return v

    @invariance
    @classmethod
    def _currency_uppercase(cls, data: dict) -> dict:
        data["currency"] = data.get("currency", "").upper()
        return data
```

- `@field_invariance` is a `field_validator` — runs only in validation model
- `@invariance` is a `model_validator(mode="after")` — runs only in validation model. Do NOT return self (the wrapper does it).

## Mutation System

- `BaseGuarded.__setattr__` and `__delattr__` enforce mutation state:
  - `BLOCK` — no mutation (default after `__init__`)
  - `PASS` — mutation allowed (entered automatically by public method wrappers via `_wrap_public_methods`)
  - `INHERIT` — bypasses `_can_mutate()` and `_mutation_status` (entered by `@inherit_context` or during `__init__`)
- `__getattribute__` returns `make_immutable(value)` when mutation is blocked:
  - `list` → `ImmutableList` (blocks append, extend, __setitem__, etc.)
  - `dict` → `ImmutableDict`
  - `set` → `ImmutableSet`
  - Custom objects → dynamically created `Immutable{ClassName}` subclass
- `BaseSealed._mutation_status` returns `INHERIT` during init, `BLOCK` otherwise (even for PASS) — truly sealed
- `BaseBehaviour._mutation_status` returns `INHERIT` for any non-BLOCK state — allows mutation inside methods
- `@inherit_context` on a method causes `_wrap_public_methods` to wrap it with `INHERIT` context (via `super_attrs` lookup)
- During `__init__`, `BaseGuarded` enters `INHERIT` context, allowing temporary mutation for `__post_init__`

## Event System

```python
from aod.events import Event

class OrderPlaced(Event):
    order_id: str

# Inside an Entity, RootEntity, or ValueObject:
self._event_emitter.emit(OrderPlaced(order_id="..."))
```

Events are immutable (`BaseSealed`). The `emitted_at` field is auto-set at construction.

### `__post_init__` Hook

Defined on `BaseValidator` (empty), called from `BaseValidator.__init__`. Only runs on **normal `__init__`**, never on `reconstruct` (check via `_use_raw_model` ContextVar).

```python
class User(RootEntity):
    id: int

    def __post_init__(self):
        self._event_emitter.emit(UserCreatedEvent(user_id=self.id))
```

Works for `Entity`, `RootEntity`, `ValueObject`, `Service`, `UseCase`, and `Projection` classes. For `BaseGuarded` subclasses, `__mutating_context__` exists before `super().__init__()` (created in `BaseGuarded.__init__`), so public methods and field mutation work during the hook (INHERIT context active).

### EventCollector

Capture events across aggregate boundaries (for testing or for
flushing to an outbox at the end of a use case):

```python
from aod.events import EventCollector

with EventCollector() as events:
    order.place(item)
    order.ship()
# events contains OrderPlaced and OrderShipped
```

`__enter__` returns the list of captured events (not the collector
itself). State is held in a `ContextVar`, so it's per-task isolated
but doesn't support nested collectors. When a UseCase calls `run()`,
it opens its own `EventCollector` which replaces any outer one during
execution. See `docs/core/event_emitter.md` for details.

## BoundedContext

```python
from aod.domain import BoundedContext

sales = BoundedContext(aggregate_roots=[Product, Customer, Order])
inventory = BoundedContext(
    aggregate_roots=[Product, Warehouse],
    services=[InventoryService],
)
```

Constructor only accepts `aggregate_roots` (RootEntity subclasses) and `services` (Service subclasses). Discovers `entities` and `value_objects` recursively from field type hints. Runs type checks at construction:
- `check_root_entity` — forbids RootEntity references in fields
- `check_value_object` — forbids Entity references in ValueObject fields
- `check_service` — forbids non-root Entity in service method params/returns
### Tests
- `code/tests/core/test_post_init.py` — 22 tests covering `__post_init__` for Entity, RootEntity, ValueObject, inheritance, event emission, public method calls, and reconstruct suppression.
- `code/tests/application/test_use_case.py` — 57 tests covering UseCase instantiation, event collection, immutability, exceptions, inheritance, `__post_init__`, `__repr__`, multiple runs, UoW auto-commit/rollback, logger auto-log, and edge cases.
- `code/tests/domain/test_service.py` — 17 tests covering Service instantiation, event emission, mutability via methods, `__post_init__`, inheritance, private methods, collection, and event isolation.
- `code/tests/application/test_port.py` — 16 tests covering Port instantiation, abstract enforcement, method wrapping, mutation blocking, and built-in port types (Logger, EventBus, UnitOfWork).
- `code/tests/infrastructure/test_projection_classes.py` — 52 tests covering ReadProjection, WriteProjection, Projection, async variants, event capture, commit context, rollback on error.
- `code/tests/infrastructure/test_inject.py` — 34 tests covering inject_adapters for UseCase, AsyncUseCase, and Projection classes.
- `code/tests/infrastructure/test_container.py` — 36 tests covering get_port, get_handler, get_uow, duplicate validation.
- `code/tests/core/test_base_operation_port_check.py` — 8 tests covering UseCase/Projection field validation: infra handler rejection, app handler acceptance, non-Port fields allowed.

## Development Commands

```bash
uv run pytest code/tests -q
uv run ruff check code/ && uv run ruff format --check code/  # Lint + format check
ty check                           # Type check
```

## Conventions

- Python 3.14+ — use `|` for unions, `type[X]`, `Self`, etc.
- Keyword-only arguments everywhere
- No comments in source code
- Tests mirror source structure under `code/tests/`
