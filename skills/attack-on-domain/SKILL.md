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

Create the concrete Handler implementations and Sessions. Rename infrastructure handlers to avoid confusion with application protocols.

```python
from aod.infrastructure import CommandHandler as InfraCommandHandler, QueryHandler as InfraQueryHandler, Session

class PlaceOrderHandler(InfraCommandPort[PlaceOrder]):
    session: Session
    def handle(self, command: PlaceOrder) -> None:
        # Save order to database
        ...

class GetOrderHandler(InfraQueryPort[GetOrder]):
    session: Session
    def handle(self, query: GetOrder) -> Order | None:
        # Load order from database
        ...
```

### Step 4: Container and Injection

Wire everything together with the AdapterContainer and inject dependencies.

```python
from aod.infrastructure import AdapterContainerBase, inject_adapters

class AppContainer(AdapterContainerBase):
    sessions: set = {SqlSession}
    handlers: list = [PlaceOrderHandler, GetOrderHandler]

container = AppContainer()
place_order = inject_adapters(container, PlaceOrderUseCase)
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
| `from aod.infrastructure import ReadProjection, WriteProjection, Projection` | Projection base classes |
| `from aod.infrastructure import AsyncReadProjection, AsyncWriteProjection, AsyncProjection` | Async projection classes |
| `from aod.infrastructure import ReadModel, WriteModel` | Projection data models |
| `from aod.infrastructure import inject_adapters` | Dependency injection for UseCases and Projections |
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
| `from aod.testing.doubles.application import SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache` | Sync test doubles |
| `from aod.testing.doubles import SpySession, SpyAsyncSession` | Session test doubles |
| `from aod.testing.doubles.application.async_ import SpyLogger, SpyEventBus, SpyUnitOfWork, SpyCache` | Async test doubles |

## Domain Primitives

### ValueObject vs Entity vs RootEntity

| | ValueObject | Entity | RootEntity |
|---|---|---|---|
| **Identity** | No identity | Has identity | Has identity |
| **Mutable** | No | Yes (inside methods) | Yes (inside methods) |
| **Use in UseCase** | No | No | Yes |
| **Example** | Money, Email, Address | OrderLine, Address | Order, User, Product |

**ValueObject** — Immutable, no identity. Two `Money(amount=10, currency="USD")` are equal. Used as fields inside other objects.

**Entity** — Mutable, has identity. Two `User(id="1", name="Alice")` are different objects (different identity). Cannot be used directly in UseCases.

**RootEntity** — The aggregate root. Entry point for all operations. This is what UseCases, Commands, and Queries work with. All other entities in the aggregate are nested inside the RootEntity's fields.

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
```

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

### CommandHandler / QueryHandler

**Application layer** (`aod.application`): Protocol definitions for handlers.

**Infrastructure layer** (`aod.infrastructure`): Concrete implementations with session injection.

**Runtime type checking**: Handlers verify that the command/query passed to `handle()` matches the generic type parameter. If not, raises `TypeError`.

**Session**: The database abstraction. No repositories or stores — Session IS the data access layer.

```python
# Application layer — protocol (what the UseCase depends on)
from aod.application import CommandPort, QueryPort

# Infrastructure layer — implementation (rename to avoid confusion)
from aod.infrastructure import CommandHandler as InfraCommandHandler, QueryHandler as InfraQueryHandler, Session
from aod.domain import PrivateField

# Create your Session subclass
class MemorySession(Session):
    _data: dict = PrivateField(default_factory=dict)

    def execute(self, operation: object) -> object:
        # Write operations
        ...

    def query(self, operation: object) -> object:
        # Read operations
        ...

    def begin(self) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

    def close(self) -> None:
        ...

    def is_dirty(self) -> bool:
        return False

# Handlers use YOUR session type, not abstract Session
class PlaceOrderHandler(InfraCommandPort[PlaceOrder]):
    session: MemorySession  # Concrete type — injected by container
    def handle(self, command: PlaceOrder) -> None:
        self.session.execute(...)

class GetOrderHandler(InfraQueryPort[GetOrder]):
    session: MemorySession  # Concrete type — injected by container
    def handle(self, query: GetOrder) -> Order | None:
        return self.session.query(...)

# Type checking works automatically
handler = PlaceOrderHandler()
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

### Container and Injection

Wire dependencies together.

```python
from aod.infrastructure import AdapterContainerBase, inject_adapters

class AppContainer(AdapterContainerBase):
    sessions: set = {SqlSession}
    handlers: list = [PlaceOrderHandler, GetOrderHandler]

container = AppContainer()
place_order = inject_adapters(container, PlaceOrderUseCase)
place_order.run(order_id="1", product_id="p1", quantity=2, price=9.99)
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
class User(RootEntity):
    id: int
    name: str

    def __post_init__(self) -> None:
        self._event_emitter.emit(UserCreated(user_id=self.id))
```

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

## Conventions

- Python 3.14+ — use `|` for unions, `type[X]`, `Self`, etc.
- No repositories — use `CommandHandler`/`QueryHandler` for database access
- Application handlers (`aod.application`) = protocols
- Infrastructure handlers (`aod.infrastructure`) = implementations with session injection
