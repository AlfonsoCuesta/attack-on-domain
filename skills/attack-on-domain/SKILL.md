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
| `from aod import BoundedContext, Entity, RootEntity, ValueObject, Service` | Domain primitives |
| `from aod import Field, PrivateField` | Field wrappers |
| `from aod import DomainEvent` | Event base class |
| `from aod.validation import field_invariance, invariance, super_context` | Validation decorators |
| `from aod.validation import AfterValidator, BeforeValidator` | Pydantic validators |
| `from aod.exceptions import DomainException, MutationForbiddenException` | Public exceptions |
| `from aod.diagram import render_html, show` | Interactive diagram |

Never import from `aod._internal` in user code.

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

## Dual-Model Validation

Each user class gets **two** Pydantic models at class creation:
- `__validation_model__` — includes all field constraints, `@field_invariance` validators, `@invariance` model validators
- `__raw_model__` — strips all validators

`__init__` uses the validation model. `from_existing()` uses the raw model (bypasses re-validation).

## Validation Decorators

```python
from aod.validation import field_invariance, invariance

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

- `BaseGuarded.__setattr__` enforces mutation state:
  - `BLOCK` — no mutation (default after `__init__`)
  - `PASS` — mutation allowed (entered automatically by public method wrappers via `_wrap_public_methods`)
  - `SUPER` — bypasses `_can_mutate()` (entered by `@super_context`)
- `__getattribute__` returns `make_immutable(value)` when mutation is blocked:
  - `list` → `ImmutableList` (blocks append, extend, __setitem__, etc.)
  - `dict` → `ImmutableDict`
  - `set` → `ImmutableSet`
  - Custom objects → dynamically created `Immutable{ClassName}` subclass

## Event System

```python
from aod import DomainEvent

class OrderPlaced(DomainEvent):
    order_id: str

# Inside an Entity, RootEntity, or ValueObject:
self._event_emitter.emit(OrderPlaced(order_id="..."))
```

Events are immutable (`BaseSealed`). The `emmited_at` field (note the typo, it's established API, do NOT fix it) is auto-set at construction.

### `__post_init__` Hook

Defined on `BaseValidator` (empty), triggered from `BaseGuarded.__init__`. Only runs on **normal `__init__`**, never on `from_existing`.

```python
class User(RootEntity):
    id: int

    def __post_init__(self):
        self._event_emitter.emit(UserCreatedEvent(user_id=self.id))
```

Works for `Entity`, `RootEntity`, and `ValueObject`. Public methods can be called and fields mutated during the hook (runs after `__mutating_context__` exists).

Use `EventCollector` to capture events across objects:

```python
from aod._internal.core.event_emitter import EventCollector

with EventCollector() as events:
    order.place(...)
    # events now contains all DomainEvents emitted
```

## BoundedContext

```python
from aod import BoundedContext

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
- `code/tests/core/test_post_init.py` — 22 tests covering `__post_init__` for Entity, RootEntity, ValueObject, inheritance, event emission, public method calls, and from_existing suppression.

## Development Commands

```bash
uv run pytest code/tests -q         # Run all tests (199)
uv run ruff check code/ && uv run ruff format --check code/  # Lint + format check
uv run mypy code/                   # Type check
```

## Conventions

- Python 3.14+ — use `|` for unions, `type[X]`, `Self`, etc.
- Keyword-only arguments everywhere
- No comments in source code
- Tests mirror source structure under `code/tests/`
