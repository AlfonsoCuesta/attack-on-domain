# DDD Concepts to attack-on-domain

This page maps standard Domain-Driven Design concepts to their implementation in `attack-on-domain`.

## Core Building Blocks

### Entity

**DDD:** Mutable object with a unique identity that persists over time. Two entities with the same attributes are different if they have different identities.

**AoD:** `Entity` and `RootEntity` with automatic mutation guards.

| DDD | AoD |
|-----|-----|
| Entity has identity | Object identity (no custom `__eq__`). Two separate instances are never equal, even with the same values |
| Entity can change state | Mutate fields inside public methods |
| Entity compared by identity | Default object identity (`is`). Add your own `__eq__` based on an `id` field if needed |

```python
class User(Entity):
    id: str
    name: str

    def rename(self, new_name: str) -> None:
        self.name = new_name
```

### Value Object

**DDD:** Immutable object defined by its attributes, not its identity. Two VOs with the same values are interchangeable.

**AoD:** `ValueObject` — always immutable, compared by value.

| DDD | AoD |
|-----|-----|
| Immutable by contract | All mutation is blocked after construction |
| Compared by value | Structural equality automatically |
| No identity | No `id` field needed |

```python
class Money(ValueObject):
    amount: float
    currency: str
```

### Aggregate / Aggregate Root

**DDD:** A cluster of domain objects treated as a single unit. The aggregate root is the only entry point; external objects reference it by ID, never by object reference.

**AoD:** `RootEntity` marks the aggregate root. `BoundedContext` enforces nesting rules — `RootEntity` cannot be nested inside other entities.

| DDD | AoD |
|-----|-----|
| Aggregate root | `RootEntity` subclass |
| Consistency boundary | Aggregate root methods enforce invariants |
| Child entities | Nested `Entity` objects inside the `RootEntity` |
| Reference by ID | Use `user_id: str` instead of `user: User` |

```python
class OrderLine(Entity):
    product_id: str
    quantity: int

class Order(RootEntity):
    id: str
    lines: list[OrderLine]

    def add_line(self, product_id: str, quantity: int) -> None:
        self.lines.append(OrderLine(product_id=product_id, quantity=quantity))
```

### Domain Event

**DDD:** A record of something significant that happened in the domain. Events are immutable and timestamped.

**AoD:** `Event` — immutable, auto-timestamped with `emitted_at`. Emitted via `_event_emitter` on any domain object.

| DDD | AoD |
|-----|-----|
| Record of occurrence | Subclass `Event` with relevant fields |
| Timestamped | `emitted_at` is set automatically |
| Emitted by aggregate | Use `self._event_emitter.emit(...)` |
| Collected for processing | UseCases auto-collect events |

```python
class OrderPlaced(Event):
    order_id: str
    total: float

class Order(RootEntity):
    id: str
    total: float

    def place(self) -> None:
        self._event_emitter.emit(OrderPlaced(order_id=self.id, total=self.total))
```

### Domain Service

**DDD:** A stateless operation that does not naturally belong to an entity or value object. Often orchestrates multiple aggregates.

**AoD:** `Service` — stateless, with event emission and field mutation inside methods.

| DDD | AoD |
|-----|-----|
| Stateless operation | Subclass `Service` |
| Can emit events | Via `_event_emitter` |
| Method constraints | Non-root `Entity` forbidden in method signatures |

```python
class PricingService(Service):
    def calculate_total(self, items: list[OrderItem], tax_rate: float) -> float:
        subtotal = sum(item.price * item.quantity for item in items)
        return subtotal * (1 + tax_rate)
```

### Domain Invariant

**DDD:** A business rule that must always be true. Enforced at construction time or on state change.

**AoD:** `@field_invariance` (field-level) and `@invariance` (model-level). Violations raise `InvarianceException`.

| DDD | AoD |
|-----|-----|
| Field-level rule | `@field_invariance("field_name")` |
| Cross-field rule | `@invariance` |
| Violation | `InvarianceException` |

```python
class Money(ValueObject):
    amount: float
    currency: str

    @field_invariance("amount")
    def amount_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Amount must be positive")
        return v
```

### Bounded Context

**DDD:** A boundary within which a particular domain model is defined and consistent. Each context has its own ubiquitous language.

**AoD:** `BoundedContext` groups `RootEntity` classes and `Service` classes, discovers child types automatically, and enforces DDD constraints.

| DDD | AoD |
|-----|-----|
| Context boundary | `BoundedContext(aggregate_roots=[...], services=[...])` |
| Type discovery | Automatically finds child entities and VOs |
| Global validation | `App` composes contexts and detects duplicates |

```python
product_context = BoundedContext(aggregate_roots=[Product], name="products")
order_context = BoundedContext(aggregate_roots=[Order], name="orders")
app = App("ecommerce", product_context, order_context)
```

## Application Layer

### Command / Query

**DDD:** Commands express intent to change state; Queries express intent to read state. Both are immutable.

**AoD:** `Command[TEntity, TResult]` and `Query[TEntity, TResult]` with type-validated generic parameters.

| DDD | AoD |
|-----|-----|
| Immutable request | `Command` / `Query` |
| Entity binding | `TEntity` must be a `RootEntity` |
| Result type | `TResult` on `Query` must contain a `RootEntity` |

```python
class CreateUser(Command[User, None]):
    user_id: str
    name: str
    email: str

class GetUser(Query[User, User | None]):
    user_id: str
```

### Use Case (Application Service)

**DDD:** Orchestrates domain objects to fulfill a user goal. Coordinates domain logic, transactions, and infrastructure.

**AoD:** `UseCase` with auto-wired dependencies, transaction management, event collection, logging, and cache flushing.

| DDD | AoD |
|-----|-----|
| Orchestration | `run()` method |
| Database access | Via `CommandPort[T]` / `QueryPort[T]` fields |
| External services | Via custom `Port` subclasses |
| Transaction | Auto-managed via `UnitOfWork` |
| Events | Auto-collected and published |

```python
class CreateUserUseCase(UseCase):
    save_user: CommandPort[CreateUser]

    def run(self, user_id: str, name: str, email: str) -> None:
        user = User(id=user_id, name=name, email=email)
        self.save_user.handle(CreateUser(user_id=user_id, name=name, email=email))
```

### Repository (Data Access)

**DDD:** Mediates between the domain and data mapping layers. Provides collection-like access to aggregates.

**AoD:** No `Repository` class. Use `CommandHandler[C]` and `QueryHandler[Q]` instead. UseCases depend on `CommandPort[T]` / `QueryPort[T]`, never on repositories.

| DDD | AoD |
|-----|-----|
| Save aggregate | `CommandHandler` with `self.session.execute(...)` |
| Load aggregate | `QueryHandler` with `self.session.query(...)` |
| Interface | `CommandPort[T]` / `QueryPort[T]` on the UseCase |

```python
class SaveUserHandler(CommandHandler[CreateUser]):
    def handle(self, command: CreateUser) -> None:
        user = User(id=command.user_id, name=command.name, email=command.email)
        self.session.execute(user)
```

### Ports and Adapters (Hexagonal Architecture)

**DDD:** Ports define interfaces; adapters provide implementations. The core depends on ports, not adapters.

**AoD:** The framework is built on ports and adapters: `Port` base class, `CommandPort`/`QueryPort` for handlers, and built-in ports for cross-cutting concerns.

| DDD | AoD |
|-----|-----|
| Primary port | `UseCase` (driving) |
| Secondary port | `CommandPort[T]`, `QueryPort[T]`, custom `Port` |
| Adapter | Infrastructure handlers, `CommandHandler[C]`, `QueryHandler[Q]` |
| DI container | `AdapterContainer.adapt()` |

## Mapping Summary

| DDD Concept | AoD Class / Mechanism |
|-------------|----------------------|
| Entity | `Entity` |
| Aggregate Root | `RootEntity` |
| Value Object | `ValueObject` |
| Domain Event | `Event` |
| Domain Service | `Service` |
| Domain Invariant | `@field_invariance`, `@invariance` |
| Bounded Context | `BoundedContext`, `App` |
| Command | `Command[TEntity, TResult]` |
| Query | `Query[TEntity, TResult]` |
| Application Service | `UseCase`, `AsyncUseCase` |
| Repository | `CommandHandler[C]`, `QueryHandler[Q]` |
| Port | `Port`, `CommandPort[T]`, `QueryPort[T]` |
| Adapter | Infrastructure handler implementations |
| DI Container | `AdapterContainer` |
| Transaction | `UnitOfWork`, `AsyncUnitOfWork` |
| Event Bus | `EventBus`, `AsyncEventBus` |
| Cache | `Cache`, `AsyncCache` |

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="quickstart.md">Quick Start</a></h3>
<p>Build a complete example in 5 minutes</p>
</div>

<div class="feature-card">
<h3><a href="concepts.md">DDD Concepts</a></h3>
<p>Deeper explanation of the theory</p>
</div>

<div class="feature-card">
<h3><a href="../domain/index.md">Domain Objects</a></h3>
<p>Entity, ValueObject, Service API</p>
</div>

<div class="feature-card">
<h3><a href="../application/index.md">Application Layer</a></h3>
<p>UseCase, Ports, Contracts</p>
</div>

</div>