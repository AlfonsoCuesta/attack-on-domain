---
name: attack-on-domain
description: "Use ONLY when the user is building a Domain-Driven Design system with this library. Covers entities, value objects, bounded contexts, domain events, the dual-model Pydantic validation system, and the interactive DDD diagram generator."
---

# attack-on-domain — Domain-Driven Design Library

Python 3.14+ DDD building blocks with Pydantic v2 under the hood.

Source code is under `code/` (mapped as package root in `pyproject.toml`).

## Public API

| Import | What |
|--------|------|
| `from aod.domain import BoundedContext, Entity, RootEntity, ValueObject, Service` | Domain primitives |
| `from aod.domain import Field, PrivateField` | Field wrappers |
| `from aod.domain import DomainEvent` | Event base class |
| `from aod.domain.validation import field_invariance, invariance, inherit_context` | Validation decorators |
| `from aod.domain.validation import AfterValidator, BeforeValidator` | Pydantic validators |
| `from aod.exceptions import DomainException, MutationForbiddenException` | Public exceptions |
| `from aod.diagram import render_html, show` | Interactive diagram |
| `from aod.domain import EventCollector` | Cross-aggregate event capture |
| `from aod.application import UseCase` | UseCase base class |
| `from aod.application import Command, Query, Projection, Repository` | Application layer |
| `from aod.infrastructure import CommandHandler, QueryHandler, ProjectionHandler` | Infrastructure layer |

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
- **Immutable** — inherits `BaseSealed`, stateless service pattern
- `_event_emitter` via `PrivateField(default_factory=EventEmitter)`, same as Entity/ValueObject
- Methods must not accept or return non-root `Entity` types (enforced at `BoundedContext` construction)
- Public methods do **not** allow mutation (BaseSealed blocks PASS context)

### UseCase
- `UseCase` is the base for application-layer use cases, available at `from aod.application import UseCase`
- Extends `BaseSealed` — immutable from outside
- Declares `events: list[Event] = Field(default_factory=list, init=False)` for collected events
- `run()` is abstract, decorated with `@inherit_context` so mutation is allowed inside (INHERIT bypasses seal)
- `__init_subclass__` auto-wraps `run()` with an `EventCollector` and captures events into `self.events`
- `uc.events` returns `ImmutableList` from outside (mutation blocked, iteration/indexing works)
- `__skip_method_wrapping__` is `True` on UseCase, so `_wrap_public_methods` stops at UseCase (the abstract `run` is never wrapped by the public-method system; the event-collector wrapping handles it)
- Works with inheritance chains (UseCase → Abstract → Concrete)

### Repository Layer

CQRS-inspired repository abstraction at `from aod.application import ...`:

- **`Command[TEntity, TResult]`** / **`Query[TEntity, TResult]`** — immutable value objects for writes/reads; validate `TEntity` is a `RootEntity` subclass
- **`Projection[TResult]`** — immutable data class for read models (extends `BaseSealed`, no entity restriction)
- **`CommandHandler[C]`** / **`QueryHandler[Q]`** / **`ProjectionHandler[P]`** — abstract bases with `handle()` method; validate generic param at class creation
- **`Repository[TEntity]`** — receives `command_handlers`, `query_handlers`, and `projection_handlers` in `__init__`; dispatches via `command()` / `query()` / `projection()`

```python
from aod.application import Command, Projection, Repository
from aod.infrastructure import CommandHandler, ProjectionHandler

class CreateUser(Command[User, User]):
    name: str

class CreateUserHandler(CommandHandler[CreateUser]):
    def handle(self, cmd: CreateUser) -> User:
        ...

class UserCount(Projection[int]):
    pass

class UserCountHandler(ProjectionHandler[UserCount]):
    def handle(self, projection: UserCount) -> int:
        return 42

repo = Repository[User](
    command_handlers=[CreateUserHandler()],
    projection_handlers=[UserCountHandler()],
)
repo.command(CreateUser(name="Alice"))
repo.projection(UserCount())
```

Handler type resolution uses `__orig_bases__` introspection (`get_generic_arg_from_mro` in `type_handlers/generic_utils.py`).

## Dual-Model Validation

Each user class gets **two** Pydantic models at class creation:
- `__validation_model__` — includes all field constraints, `@field_invariance` validators, `@invariance` model validators
- `__raw_model__` — strips all validators

`__init__` uses the validation model. `ReconstructMixin.reconstruct()` uses the raw model (bypasses re-validation). Only classes that mix in `ReconstructMixin` (`Entity`, `ValueObject`, `RootEntity`) have `reconstruct()` — `Service` and `UseCase` do not.

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
- `@inherit_context` on a method causes `_wrap_public_methods` to wrap it with `INHERIT` context (via `super_attrs` lookup)
- During `__init__`, `BaseGuarded` enters `INHERIT` context, allowing temporary mutation for `__post_init__`

## Event System

```python
from aod.domain import DomainEvent

class OrderPlaced(DomainEvent):
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

Works for `Entity`, `RootEntity`, `ValueObject`, `Service`, and `UseCase`. For `BaseGuarded` subclasses, `__mutating_context__` exists before `super().__init__()` (created in `BaseGuarded.__init__`), so public methods and field mutation work during the hook (INHERIT context active).

### EventCollector

Capture events across aggregate boundaries (for testing or for
flushing to an outbox at the end of a use case):

```python
from aod.domain import EventCollector

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

## Interactive Diagram

```python
from aod.diagram import render_html, show

# Generate HTML string:
html = render_html(sales, inventory)

# Open in browser:
show(sales, inventory)
```

Produces an interactive hand-drawn (rough.js) diagram with:
- Node cards for each type, color-coded by stereotype
- Aggregate root containers (rough.js rectangles)
- Bounded context containers grouping all types per context
- Arrows for entity-to-entity field references
- Drag, pan, zoom

### Tests
- `code/tests/core/test_post_init.py` — 22 tests covering `__post_init__` for Entity, RootEntity, ValueObject, inheritance, event emission, public method calls, and reconstruct suppression.
- `code/tests/application/test_use_case.py` — 42 tests covering UseCase instantiation, event collection, immutability, exceptions, inheritance, `__post_init__`, `__repr__`, multiple runs, and edge cases.
- `code/tests/domain/test_service.py` — 17 tests covering Service instantiation, event emission, immutability, `__post_init__`, inheritance, private methods, collection, and event isolation.
- `code/tests/application/test_repository.py` — 45 tests covering Command/Query validation, handler type checking, dispatch, duplicates, and edge cases.

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
