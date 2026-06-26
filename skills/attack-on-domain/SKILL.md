---
name: attack-on-domain
description: "Use ONLY when the user is building a Domain-Driven Design system with this library. Covers entities, value objects, bounded contexts, domain events, and the Pydantic validation system."
---

# attack-on-domain — Domain-Driven Design Library

Python 3.14+ DDD building blocks with Pydantic v2 under the hood.

Source code is under `code/` (mapped as package root in `pyproject.toml`).

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

### Step 2: Application Layer — UseCases, Commands/Queries, Handlers (APPLICATION)

Create Commands, Queries, and UseCases. UseCases depend on `CommandPort[Command]` and `QueryPort[Query]` from `aod.application` — NOT on repositories or custom ports for database access. All database communication goes through handlers.

```python
from aod.application import UseCase, Command, Query, CommandHandler, QueryHandler

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

    def run(self, order_id: str, product_id: str, quantity: int, price: float) -> None:
        order = Order(id=OrderId(value=order_id))
        order.add_line(product_id, quantity, price)
        self.place_order.handle(PlaceOrder(
            order_id=order_id,
            product_id=product_id,
            quantity=quantity,
            price=price,
        ))
```

### Step 3: Infrastructure Layer — Implementations

Create the concrete Handler implementations and Sessions.

**Session** is the data access abstraction. There are no repositories, no stores — the Session IS how you read and write. Each handler declares a `session` field with the concrete session type it needs, and the container injects the matching instance.

**Session lifecycle is managed by the UnitOfWork (UoW)** — never call `begin()`, `commit()`, or `rollback()` manually on a session. The UseCase wrapper handles it automatically.

```python
from aod.infrastructure import CommandHandler, QueryHandler, Session
from aod.domain import PrivateField

# Your database session
class PostgresSession(Session):
    _conn: object = PrivateField(default=None)

    def execute(self, operation: object) -> None:
        ...

    def query(self, operation: object) -> object:
        ...

    def begin(self) -> None:
        self._conn.begin()

    def commit(self) -> None:          # raises CommitOutsideUnitOfWorkError
        self._conn.commit()            # if called outside a UseCase

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def is_dirty(self) -> bool:
        return ...

# CommandHandler — writes, UoW manages transactions
class PlaceOrderHandler(CommandHandler[PlaceOrder]):
    session: PostgresSession

    def handle(self, command: PlaceOrder) -> None:
        self.session.execute("INSERT INTO orders ...")

# QueryHandler — reads only, no transaction needed
class GetOrderHandler(QueryHandler[GetOrder]):
    session: PostgresSession

    def handle(self, query: GetOrder) -> Order | None:
        return self.session.query("SELECT * FROM orders WHERE id = ...")
```

### Step 4: Container and Injection

Wire everything together with `AdapterContainer`. It discovers sessions, handlers, and custom ports, then auto-wires them into UseCases and Projections via `adapt_use_case()` / `adapt_projection()`.

```python
from aod.infrastructure import AdapterContainer

container = AdapterContainer(sessions={PostgresSession}, handlers=[PlaceOrderHandler, GetOrderHandler])
place_order = container.adapt_use_case(PlaceOrderUseCase)
place_order.run(order_id="1", product_id="p1", quantity=2, price=9.99)
```

## Public API

| Import | What |
|--------|------|
| `from aod.domain import BoundedContext, Entity, RootEntity, ValueObject, Service` | Domain primitives |
| `from aod.domain import Field` | Field wrapper with constraints |
| `from aod.domain import PrivateField` | Private fields for internal state |
| `from aod.events import Event` | Event base class |
| `from aod.events import EventCollector` | Cross-aggregate event capture |
| `from aod.domain.validation import field_invariance, invariance, inherit_context` | Validation decorators |
| `from aod.domain.validation import AfterValidator, BeforeValidator` | Pydantic validators |
| `from aod.application import UseCase` | UseCase base class |
| `from aod.application import Port` | Abstract port/gateway base class |
| `from aod.application import Logger, EventBus, UnitOfWork, Cache` | Built-in port types (sync) |
| `from aod.application.async_ import Cache, EventBus, Logger, UnitOfWork` | Async versions |
| `from aod.application import Command, Query` | Application contracts |
| `from aod.application import CommandPort, QueryPort` | Application handler protocols |
| `from aod.infrastructure import CommandHandler, QueryHandler` | Infrastructure handler implementations |
| `from aod.infrastructure import Session` | Database abstraction base |
| `from aod.infrastructure.async_ import Session` | Async database abstraction |
| `from aod.infrastructure import ReadProjection, WriteProjection, Projection` | Projection base classes |
| `from aod.infrastructure import AsyncReadProjection, AsyncWriteProjection, AsyncProjection` | Async projection classes |
| `from aod.infrastructure import ReadModel, WriteModel` | Projection data models |
| `from aod.infrastructure import AdapterContainer` | Container with `adapt_use_case()` / `adapt_projection()` |
| `from aod.domain import DomainException` | Domain base exception |
| `from aod.application import ApplicationException` | Application base exception |
| `from aod.infrastructure import InfrastructureException` | Infrastructure base exception |

## Testing Utilities

| Import | What |
|--------|------|
| `from aod.testing import build` | Construct domain objects skipping validation |
| `from aod.testing import events_of` | Extract events emitted by an entity/service/vo |
| `from aod.testing import assert_event_emitted, assert_no_events` | Event assertions |
| `from aod.testing import check_invariant` | Run a single invariant validator |
| `from aod.testing.doubles import Params` | `Params` objects with `.args()` and `.kwargs()` from stub calls |
| `from aod.testing.doubles import port_stub` | Create stub class from any `Port` subclass |
| `from aod.testing.doubles import spy_adapter_container` | Container with stubbed sessions/ports/handlers |
| `from aod.testing.doubles.application import SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache` | Sync test doubles |
| `from aod.testing.doubles import SpySession, SpyAsyncSession` | Session test doubles |
| `from aod.testing.doubles.application.async_ import SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache` | Async test doubles |

## Domain Primitives

### ValueObject vs Entity vs RootEntity

| | ValueObject | Entity | RootEntity |
|---|---|---|---|---|
| **Identity** | No identity | Has identity | Has identity |
| **Mutable** | No | Yes (inside methods) | Yes (inside methods) |
| **Equality** | By all public fields | By `EntityId` only | By `EntityId` only |
| **Use in UseCase** | No | No | Yes |
| **Example** | Money, Email, Address | OrderLine, Address | Order, User, Product |

**ValueObject** — Immutable, no identity. Compared by value: two VOs with identical public fields are equal. Used as fields inside other objects.

**Entity** — Mutable, has identity. Compared only by their `EntityId`: two Entities with the same id are equal regardless of other fields. Cannot be used directly in UseCases.

**RootEntity** — Same as Entity: compared by `EntityId`. The aggregate root, entry point for UseCases, Commands, and Queries.

```python
from aod.domain import RootEntity, ValueObject, Entity, Field

class OrderId(ValueObject):      # ValueObject: no identity, immutable
    value: str

class OrderLine(Entity):         # Entity: has identity, mutable, but NOT used in UseCases
    id: str
    product_id: str
    quantity: int

class Order(RootEntity):         # RootEntity: the aggregate root, used in UseCases
    id: OrderId
    lines: list[OrderLine] = Field(default_factory=list)
    total: float = 0.0
```

### ValueObject

Immutable identity-less values. Cannot be changed after creation.

**DO NOT define `__init__`** — the framework generates it automatically from your field annotations.

```python
from aod.domain import ValueObject

class Money(ValueObject):
    amount: float
    currency: str

price = Money(amount=10.0, currency="USD")
price.amount = 20.0  # MutationForbiddenException!

**Equality**: Two ValueObjects with the same public fields are equal:

```python
a = Money(amount=10.0, currency="USD")
b = Money(amount=10.0, currency="USD")
assert a == b
```

Private fields (declared with `PrivateField`) are excluded from equality comparison.

### Entity

Mutable objects with identity. Can mutate fields inside public methods. NOT used directly in UseCases — only RootEntity is.

**DO NOT define `__init__`** — the framework generates it automatically from your field annotations. Just declare fields as class attributes.

```python
from aod.domain import Entity, Field
from uuid import UUID, uuid4

# Correct: fields as annotations, no __init__
class User(Entity):
    id: UUID
    name: str
    email: str

# Wrong: defining __init__ manually
class User(Entity):
    id: UUID
    name: str
    email: str

    def __init__(self, name: str, email: str, id: UUID | None = None) -> None:  # NO!
        self.id = id or uuid4()
        self.name = name
        self.email = email
```

**Equality**: Two Entities with the same `EntityId` are equal, regardless of other fields:

```python
class UserId(EntityId):
    value: str

class User(Entity):
    id: UserId
    name: str

a = User(id=UserId(value="1"), name="Alice")
b = User(id=UserId(value="1"), name="Bob")
assert a == b  # Same EntityId → equal
assert hash(a) == hash(b)
```

### RootEntity

Aggregate root. The entry point for all operations. UseCases, Commands, and Queries work ONLY with RootEntity.

**DO NOT define `__init__`** — the framework generates it automatically from your field annotations.

```python
from aod.domain import RootEntity

class Order(RootEntity):
    id: str
    total: float

class OrderLine(RootEntity):
    product_id: str
    quantity: int

# Wrong: RootEntity nested in another
class Order(RootEntity):
    id: str
    line: OrderLine  # InvalidNestedTypeError!

# Correct: reference by ID
class Order(RootEntity):
    id: str
    line_id: str
```

### Service

Stateless domain operations. Methods cannot accept or return non-root Entity types.

```python
from aod.domain import Service

class TaxCalculator(Service):
    def calculate(self, amount: float, rate: float) -> float:
        return amount * rate
```

## Application Layer

### UseCase

Application operations that orchestrate domain logic through handlers.

**IMPORTANT**: 
- UseCases work ONLY with `RootEntity` — not `Entity` or `ValueObject` directly
- UseCases communicate with the database ONLY through `CommandPort[Command]` and `QueryPort[Query]`. Do NOT create repository ports or custom ports for database access.

```python
from aod.application import UseCase, CommandHandler, QueryHandler

class PlaceOrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]
    get_order: QueryPort[GetOrder]

    def run(self, order_id: str, product_id: str, quantity: int, price: float) -> None:
        # Query existing order
        existing = self.get_order.handle(GetOrder(order_id=order_id))

        # Create and save
        order = Order(id=OrderId(value=order_id))
        order.add_line(product_id, quantity, price)
        self.place_order.handle(PlaceOrder(
            order_id=order_id,
            product_id=product_id,
            quantity=quantity,
            price=price,
        ))
```

**Rules**:
- Fields must be `CommandPort[Command]`, `QueryPort[Query]`, or `Port` subclasses
- Values are passed as parameters to `run()`, not declared as fields
- `Session` and `AsyncSession` are NOT allowed as fields
- Events emitted via `self._event_emitter.emit(...)` are auto-collected in `self.events`

### Command / Query

Immutable contracts for writes and reads.

```python
from aod.application import Command, Query

class PlaceOrder(Command[Order, None]):
    order_id: str
    product_id: str
    quantity: int
    price: float

class GetOrder(Query[Order, Order | None]):
    order_id: str
```

**Rules**:
- `Command[TEntity, TResult]` — TEntity must be a RootEntity subclass
- `Query[TEntity, TResult]` — same, and TResult must contain a RootEntity
- Fields cannot reference non-root Entity types

### Handler Types

**Application layer** (`aod.application`): `CommandPort[Command]` / `QueryPort[Query]` — protocol definitions that UseCases depend on.

**Infrastructure layer** (`aod.infrastructure`): `CommandHandler[C]` / `QueryHandler[Q]` — concrete implementations.

### Session

Session IS the data access layer. There are no repositories, stores, or DAOs. Each handler declares a `session` field typed to its concrete session, and the container injects the correct instance.

#### Required methods

| Method | Description |
|--------|-------------|
| `begin()` | Start a new transaction |
| `commit()` | Commit the transaction. Raises `CommitOutsideUnitOfWorkError` if called outside a UnitOfWork context |
| `rollback()` | Rollback the transaction |
| `close()` | Release resources |
| `is_dirty()` | Return `True` if there are uncommitted changes |

Add any domain-specific methods (e.g. `execute()`, `query()`, `get()`, `set()`) as needed.

#### Transaction flow (UnitOfWork)

The UseCase wrapper manages the transaction lifecycle automatically. Never call `begin()`, `commit()`, or `rollback()` directly on a session.

```python
# What happens inside use_case.run():
uow.begin()                         # calls session.begin() on all sessions
    # Your run() code executes here
    # CommandHandler.handle() writes through session.execute()
    # QueryHandler.handle() reads through session.query()
# If run() succeeds:
uow.commit()                        # calls session.commit() only on dirty sessions
# If run() fails:
uow.rollback()                      # calls session.rollback() only on dirty sessions
```

The `commit()` method on every Session subclass is auto-decorated at class creation time. It checks a `ContextVar` flag (`_CommitContext`) that is set to `True` only inside `uow.commit()`. If someone calls `session.commit()` directly outside a UseCase, it raises `CommitOutsideUnitOfWorkError` immediately.

```python
class PostgresSession(Session):
    def commit(self) -> None:
        # This will raise CommitOutsideUnitOfWorkError if called outside a UseCase
        self._conn.commit()

# Outside a UseCase — this fails:
session.commit()  # CommitOutsideUnitOfWorkError!
```

#### QueryHandlers don't commit

Query handlers only read data. They do not participate in the transaction lifecycle — no `begin()`, no `commit()`, no `rollback()`. The UseCase wrapper only manages transactions for CommandHandlers (writes). QueryHandlers simply read through the session and return results.

```python
class GetOrderHandler(QueryHandler[GetOrder]):
    session: PostgresSession

    def handle(self, query: GetOrder) -> Order | None:
        return self.session.query("SELECT * FROM orders WHERE id = ?", query.order_id)
    # No commit — this is a read operation
```

#### Example: Complete session implementation

```python
from aod.infrastructure import Session
from aod.domain import PrivateField

class SqliteSession(Session):
    _conn: object = PrivateField(default=None)

    def execute(self, sql: str, params: dict | None = None) -> None:
        cur = self._conn.cursor()
        cur.execute(sql, params or {})

    def query(self, sql: str, params: dict | None = None) -> list[dict]:
        cur = self._conn.cursor()
        cur.execute(sql, params or {})
        return [dict(row) for row in cur.fetchall()]

    def begin(self) -> None:
        self._conn.execute("BEGIN")

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def is_dirty(self) -> bool:
        # Track writes in execute() and return True when there are pending changes
        return ...
```

#### Handlers with sessions

```python
from aod.infrastructure import CommandHandler, QueryHandler

class PlaceOrderHandler(CommandHandler[PlaceOrder]):
    session: SqliteSession  # Concrete type — injected by container

    def handle(self, command: PlaceOrder) -> None:
        self.session.execute(
            "INSERT INTO orders (id, total) VALUES (:id, :total)",
            {"id": command.order_id, "total": command.total},
        )

class GetOrderHandler(QueryHandler[GetOrder]):
    session: SqliteSession

    def handle(self, query: GetOrder) -> Order | None:
        rows = self.session.query(
            "SELECT * FROM orders WHERE id = :id",
            {"id": query.order_id},
        )
        if not rows:
            return None
        return Order(id=rows[0]["id"], total=rows[0]["total"])
```

#### Runtime type checking

Handlers verify that the command/query passed to `handle()` matches the generic type parameter:

```python
handler = PlaceOrderHandler(session=SqliteSession())
handler.handle(PlaceOrder(...))  # OK
handler.handle(OtherCommand(...))  # TypeError: Expected PlaceOrder, got OtherCommand
```

### Port

Interfaces for external dependencies (NOT for database access).

```python
from aod.application import Port
from abc import abstractmethod

class EmailGateway(Port):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None: ...

class SendEmailUseCase(UseCase):
    email: EmailGateway

    def run(self) -> None:
        self.email.send("user@example.com", "Hello", "World")
```

### Projection

Read and write data efficiently.

```python
from aod.infrastructure import ReadProjection, WriteProjection, Projection, ReadModel, WriteModel

class UserReadModel(ReadModel):
    user_id: str

class UserListProjection(ReadProjection):
    session: MongoSession  # Always called 'session', with specific type

    def read(self, model: ReadModel) -> list[User]:
        raw = self.session.query("SELECT * FROM users")
        return [User(**item) for item in raw]

class UserWriteModel(WriteModel):
    user_id: str
    name: str

class UserUpdateProjection(WriteProjection):
    session: MongoSession  # Always called 'session', with specific type

    def write(self, model: UserWriteModel) -> None:
        self.session.execute(f"UPDATE users SET name = '{model.name}' WHERE id = '{model.user_id}'")
```

**Rules**:
- The field MUST be named `session` with a specific type (e.g., `MongoSession`, `SqlSession`)
- If the projection doesn't need a session, simply don't declare one
- Fields must be `Port` subclasses (no `HandlerProtocol`)
- `ReadModel` / `WriteModel` are input data classes
- `read()` must return the actual domain objects (e.g., `list[User]`), not raw data

## Infrastructure Layer

### Container

`AdapterContainer` wires sessions, handlers, and custom ports, then auto-injects them into UseCases and Projections.

```python
from aod.infrastructure import AdapterContainer

class AppContainer(AdapterContainer):
    email: EmailGateway                               # Custom ports go here
```

#### adapt_use_case

Creates a UseCase instance with all dependencies injected:

- `logger` — from container
- `event_bus` — from container
- `cache` — from container
- `uow` — a `UnitOfWork` wrapping all registered sessions (begin/commit/rollback orchestrated by the wrapper)
- Custom ports — resolved by type from container fields

```python
use_case = container.adapt_use_case(PlaceOrderUseCase)
use_case.run(order_id="1", product_id="p1", quantity=2, price=9.99)
# On success: uow.begin() → run() → uow.commit() → events published → cache flushed
# On failure: uow.begin() → run() [error] → uow.rollback() → error re-raised
```

#### adapt_projection

Creates a Projection instance with dependencies:

- `logger`, `event_bus`, `cache` — from container
- `session` — resolved by type from container's registered sessions
- Custom ports — resolved by type from container fields

```python
projection = container.adapt_projection(UserListProjection)
users = projection.read(UserReadModel(user_id="1"))
```

#### Overrides

Both methods accept keyword overrides to replace specific dependencies for testing:

```python
# Override just the logger for this specific use case
uc = container.adapt_use_case(PlaceOrderUseCase, logger=SpyLogger())
```

## Validation

### Field Validation

Use Pydantic's `Field` with constraints:

```python
from aod.domain import ValueObject, Field

class Money(ValueObject):
    amount: float = Field(ge=0)
    currency: str = Field(min_length=3)
```

### Invariance Validators

Validate business rules across fields:

```python
from aod.domain import ValueObject
from aod.domain.validation import field_invariance, invariance

class Money(ValueObject):
    amount: float
    currency: str

    @field_invariance("amount")
    def _amount_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("amount must be positive")
        return v

    @invariance
    def _currency_uppercase(cls, data: dict) -> dict:
        data["currency"] = data.get("currency", "").upper()
        return data
```

## Events

```python
from aod.events import Event

class OrderPlaced(Event):
    order_id: str
    total: float

# Emit from Entity, RootEntity, or ValueObject:
self._event_emitter.emit(OrderPlaced(order_id="1", total=100.0))

# Events are auto-collected by UseCases
# Access after run(): use_case.events
```

### `__post_init__` Hook

Run code after construction (works for Entity, RootEntity, ValueObject, Service, UseCase):

```python
class UserId(EntityId):
    value: str

class User(RootEntity):
    id: UserId
    name: str

    def __post_init__(self) -> None:
        self._event_emitter.emit(UserCreated(user_id=self.id.value))
```

#### `__post_init__` vs `@invariance` / `@field_invariance`

Both run at construction but serve different purposes:

| Concern | `__post_init__` | `@invariance` / `@field_invariance` |
|---------|-----------------|--------------------------------------|
| What it does | Post-construction logic using `self` | Validates field/model values before storage |
| Use case | Emit creation events, compute derived values, call setup methods | Check business rules: "quantity must be positive", "end must be after start" |
| Runs on `reconstruct()` | No | No |
| Has `self` | Yes | No (receives `cls` and raw value) |
| Can mutate fields | Yes (during the hook) | No |

**Use `__post_init__`** for operations that need the constructed instance — emit events, compute derived fields, call setup methods.

**Use `@invariance` / `@field_invariance`** when the check can be expressed as "this value must satisfy X" — it does not need `self`.

Do NOT override `__init__` — use `__post_init__` instead.

### EventCollector

Capture events across aggregate boundaries:

```python
from aod.events import EventCollector

with EventCollector() as events:
    order.place(item)
    order.ship()
# events contains OrderPlaced and OrderShipped
```

## BoundedContext

Organize your domain into type-safe boundaries. Use in the **entry point** of your app (container), not in `domain/__init__.py`.

```python
from aod.domain import BoundedContext

# Use in your container/entry point, not in domain/__init__.py
sales = BoundedContext(aggregate_roots=[Product, Customer, Order])
inventory = BoundedContext(
    aggregate_roots=[Product, Warehouse],
    services=[InventoryService],
)
```

**Rules**:
- Only `RootEntity` subclasses as `aggregate_roots`
- Only `Service` subclasses as `services`
- Discovers entities and value objects recursively from field type hints
- No duplicate domain types across contexts

## Common Mistakes

### WRONG: Using repositories

```python
# WRONG — repositories are not part of this library
class AppointmentRepository(ABC):
    @abstractmethod
    async def save(self, appointment: Appointment) -> Appointment: ...

# WRONG — UseCase should not depend on repositories
class BookAppointmentUseCase(UseCase):
    appointment_repo: AppointmentRepository  # NO!

    async def run(self, command: BookAppointmentCommand) -> None:
        await self.appointment_repo.save(appointment)
```

```python
# CORRECT — use CommandHandler/QueryHandler
class BookAppointmentUseCase(UseCase):
    save_appointment: CommandHandler[SaveAppointment]
    get_appointment: QueryHandler[GetAppointment]

    def run(self, professional_id: str, start_time: datetime) -> None:
        appointment = Appointment(...)
        self.save_appointment.handle(SaveAppointment(...))
```

### WRONG: Using Pydantic BaseModel for commands

```python
# WRONG — BaseModel is not a Command
from pydantic import BaseModel

class BookAppointmentCommand(BaseModel):  # NO!
    professional_id: UUID
    start_time: datetime
```

```python
# CORRECT — use Command from aod.application
from aod.application import Command

class BookAppointment(Command[Appointment, None]):
    professional_id: str
    start_time: datetime
```

### WRONG: Creating handlers without UseCase

```python
# WRONG — plain class with __init__ and handle
class BookAppointmentHandler:
    def __init__(self, appointment_repo, professional_repo, event_bus):
        self._appointment_repo = appointment_repo
        self._professional_repo = professional_repo
        self._event_bus = event_bus

    async def handle(self, command: BookAppointmentCommand) -> Appointment:
        ...
```

```python
# CORRECT — inherit from UseCase
class BookAppointmentUseCase(UseCase):
    save_appointment: CommandHandler[SaveAppointment]
    get_professional: QueryHandler[GetProfessional]

    def run(self, professional_id: str, start_time: datetime) -> None:
        professional = self.get_professional.handle(GetProfessional(id=professional_id))
        appointment = Appointment(professional_id=professional_id, start_time=start_time)
        self.save_appointment.handle(SaveAppointment(...))
```

### WRONG: Defining __init__ manually

```python
# WRONG — don't define __init__
class User(Entity):
    id: UUID
    name: str

    def __init__(self, name: str, id: UUID | None = None) -> None:  # NO!
        self.id = id or uuid4()
        self.name = name
```

```python
# CORRECT — just declare fields
class User(Entity):
    id: UUID
    name: str

# Framework generates __init__ automatically
user = User(id=uuid4(), name="Alice")
```

### WRONG: Creating store/repository classes

```python
# WRONG — stores and repositories are not part of this library
class AppointmentStore:
    def save(self, appointment: Appointment) -> None: ...
    def find(self, id: UUID) -> Appointment | None: ...

class ProfessionalRepository:
    def find_by_id(self, id: UUID) -> Professional | None: ...
```

```python
# CORRECT — Session IS the data access abstraction
class MemorySession(Session):
    _data: dict = PrivateField(default_factory=dict)
    def execute(self, operation: object) -> object: ...
    def query(self, operation: object) -> object: ...

# Handlers use Session directly
class GetAppointmentHandler(QueryHandler[GetAppointment]):
    session: MemorySession  # Session replaces repositories
    def handle(self, query: GetAppointment) -> Appointment | None:
        return self.session.query(...)
```

## Schema System

The schema system provides introspection and documentation generation for your DDD application.

### Key Classes

| Class | Purpose |
|-------|---------|
| `App` | Aggregates modules, validates no duplicate types |
| `BoundedContext` | Discovers entities, value objects, services |
| `Infrastructure` | Validates handler-port wiring |
| `Module` | Validates contracts have handlers, ports have implementations |
| `AutoDoc` | Generates zensical documentation sites |

### Consistency Checks

All schema classes enforce consistency at construction time:

```python
from aod.schema import App, BoundedContext, Infrastructure, Module

# App rejects duplicate entities across modules
# BoundedContext rejects non-RootEntity as aggregate roots
# Module rejects missing handlers for contracts
# Module rejects missing implementations for ports
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `DuplicateDomainTypeError` | Same class in multiple modules | Use distinct classes or combine modules |
| `MissingHandlerError` | Contract without handler | Add handler to `Infrastructure` |
| `MissingPortError` | Port without implementation | Add implementation to `Infrastructure` ports |
| `InvalidRootEntityTypeError` | Non-RootEntity as aggregate root | Use `RootEntity` subclass |
| `InvalidServiceTypeError` | Non-Service as service | Use `Service` subclass |

### Generating Documentation with AutoDoc

```python
from aod.schema import App, BoundedContext, Module, Infrastructure, AutoDoc

bc = BoundedContext(
    aggregate_roots=[Order],
    use_cases=[OrderUseCase],
    name="Orders",
)

infra = Infrastructure(
    handlers=[PlaceOrderHandler, GetOrderHandler],
    projections=[OrderSummaryProjection],
    ports=[FakeUnitOfWork, SmtpSender],
)

mod = Module(name="orders", context=bc, infrastructure=infra)
app = App(name="MyApp", modules=[mod], description="App description")

doc = AutoDoc(
    app,
    output_dir="my-site",
    site_name="MyApp Docs",
    site_description="DDD documentation",
    repo_url="https://github.com/example/myapp",
)

doc.generate()
# Then: cd my-site && uv run zensical build --clean
```

**Docstring Inheritance**: Use `cls.__doc__` instead of `inspect.getdoc(cls)` to avoid inheriting docstrings from parent classes (e.g., `Generic`).

**Zensical Navigation**: Use `mod.domain.name` (BoundedContext name) for nav labels, not `mod.name` (module name) for better readability.

## File Organization

```
code/aod/_internal/schema/
├── app.py              # App: aggregates modules
├── bounded_context.py  # BoundedContext: type discovery + validation
├── infrastructure.py   # Infrastructure: handlers, sessions, projections
├── module.py           # Module: validates handler-port wiring
├── docs/               # Doc dataclasses for each type
└── render/             # Zensical site generator
    └── auto_doc.py     # AutoDoc: generates .md files from App

code/tests/schema/
├── test_render.py      # Unit tests with spy (no I/O)
├── test_docs.py        # Tests for doc generation
├── test_schema.py      # Tests for schema classes
└── make_example_site.py  # Example script to generate site
```

## Conventions

- Python 3.14+ — use `|` for unions, `type[X]`, `Self`, etc.
- No repositories — use `CommandHandler`/`QueryHandler` for database access
- Application handlers (`aod.application`) = protocols
- Infrastructure handlers (`aod.infrastructure`) = implementations with session injection
