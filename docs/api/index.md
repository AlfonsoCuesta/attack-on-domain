# API Reference

Comprehensive reference for all publicly importable classes, grouped by layer.

---

## Domain Layer

```python
from aod.domain import Entity, RootEntity, ValueObject, Service, Event, BoundedContext, App
from aod.domain import Field, PrivateField
from aod.domain.validation import AfterValidator, BeforeValidator, field_invariance, invariance, inherit_context
```

### Entity

```python
class Entity(ReconstructMixin, BaseGuarded)
```

Base class for mutable domain objects with identity.

#### Constructor

`Entity(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `**fields` | `Any` | Keyword arguments matching declared fields. All fields are required unless they have defaults. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `reconstruct` | `classmethod reconstruct(**kwargs) -> Self` | Create an instance skipping validation. Available via `ReconstructMixin`. |
| `copy` | `copy(**overrides) -> Self` | Create a copy with optional field overrides. |
| `__post_init__` | `__post_init__(self)` | Optional hook called after `__init__`. Runs in mutation context. |

#### Mutation Rules

- Public methods can mutate fields (auto-wrapped with mutation context).
- Direct field mutation from outside raises `MutationForbiddenException`.
- `_event_emitter` is available as a `PrivateField`.

### RootEntity

```python
class RootEntity(Entity)
```

Aggregate root marker class. Inherits all `Entity` behavior.

#### Constructor

Same as `Entity`.

#### Constraints

- Cannot be nested as a field type in other entities (enforced by `BoundedContext` type checking).
- Services and Commands/Queries can reference `RootEntity` but not non-root `Entity`.

### ValueObject

```python
class ValueObject(ReconstructMixin, BaseSealed)
```

Immutable, identity-less value object.

#### Constructor

`ValueObject(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `**fields` | `Any` | Keyword arguments matching declared fields. All fields are required unless they have defaults. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `reconstruct` | `classmethod reconstruct(**kwargs) -> Self` | Create an instance skipping validation. |

#### Constraints

- Fields cannot reference `Entity` or `RootEntity` (enforced by `BoundedContext`).
- Mutation is always blocked (`BaseSealed`).

### Service

```python
class Service(BaseBehaviour)
```

Stateless domain service with event emission capability.

#### Constructor

`Service(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `**fields` | `Any` | Keyword arguments matching declared fields. |

#### Methods

Public methods are auto-wrapped with mutation context (can mutate fields).

#### Constraints

- Method parameters and return types cannot reference non-root `Entity` (enforced by `BoundedContext`).
- `_event_emitter` is available as a `PrivateField`.

### Event

```python
class Event(BaseSealed)
```

Immutable domain event with auto-timestamp.

#### Constructor

`Event(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `**fields` | `Any` | Keyword arguments matching declared fields. |

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `emitted_at` | `datetime` | Auto-set to `datetime.now(timezone.utc)` on construction. `init=False`. |

### BoundedContext

```python
class BoundedContext
```

Groups related domain types together.

#### Constructor

```python
BoundedContext(
    aggregate_roots: Iterable[RootEntityType] | None = None,
    services: Iterable[ServiceType] | None = None,
    *,
    name: str | None = None,
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `aggregate_roots` | `Iterable[type[RootEntity]] \| None` | Root entity classes to include. |
| `services` | `Iterable[type[Service]] \| None` | Service classes to include. |
| `name` | `str \| None` | Optional name for the context. |

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `aggregate_roots` | `tuple[type[RootEntity], ...]` | Registered aggregate roots. |
| `entities` | `tuple[type[Entity], ...]` | All discovered entities. |
| `value_objects` | `tuple[type[ValueObject], ...]` | All discovered value objects. |
| `services` | `tuple[type[Service], ...]` | Registered services. |
| `name` | `str \| None` | Context name. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `describe` | `describe(self) -> list[TypeDoc]` | Return structured descriptions of all types in the context. |

#### Type Checking

When constructed, runs validation:
- All `aggregate_roots` must be `RootEntity` subclasses.
- All `services` must be `Service` subclasses.
- Recursively discovers nested entities and value objects from root entity fields.
- Validates: no non-root entities nested in root entities, no entities in value objects, no non-root entities in service method signatures.

### App

```python
class App
```

Top-level application container.

#### Constructor

```python
App(name: str, *contexts: BoundedContext)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Application name. |
| `*contexts` | `BoundedContext` | One or more bounded contexts. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `describe` | `describe(self) -> dict[str, list[TypeDoc]]` | Returns a dict mapping each context to its type descriptions. |

#### Validation

Raises `DuplicateDomainTypeError` if the same entity or service class appears in multiple contexts.

### Field

```python
Field(
    default: Any = ...,
    *,
    default_factory: Callable[[], Any] | None = ...,
    gt: SupportsGt | None = ...,
    ge: SupportsGe | None = ...,
    lt: SupportsLt | None = ...,
    le: SupportsLe | None = ...,
    multiple_of: float | None = ...,
    strict: bool | None = ...,
    min_length: int | None = ...,
    max_length: int | None = ...,
    pattern: str | re.Pattern[str] | None = ...,
    allow_inf_nan: bool | None = ...,
    max_digits: int | None = ...,
    decimal_places: int | None = ...,
    init: bool = True,
) -> Any
```

Pydantic field wrapper with all standard constraints.

### PrivateField

```python
PrivateField(default: Any = Unset(), *, default_factory: Callable[[], Any] | None = None) -> Any
```

Pydantic `PrivateAttr` wrapper. Fields are not part of the public API surface — excluded from validation models, serialization, and `__init__`.

### Validation Decorators

```python
from aod.domain.validation import field_invariance, invariance, AfterValidator, BeforeValidator, inherit_context
```

| Decorator | Description |
|-----------|-------------|
| `field_invariance(field_name)` | Validator that runs on a specific field after Pydantic validation. |
| `invariance` | Model-level validator that runs after all field validators. |
| `AfterValidator` | Pydantic `AfterValidator` wrapper. |
| `BeforeValidator` | Pydantic `BeforeValidator` wrapper. |
| `inherit_context` | Decorator to mark a method as inheriting the mutation context from its caller. |

---

## Application Layer

```python
from aod.application import UseCase, Port, Logger, EventBus, UnitOfWork, Cache, Command, Query
from aod.application import CommandPort, QueryPort
from aod.application import ApplicationException
from aod.application.async_ import UseCase, Logger, EventBus, UnitOfWork, Cache
from aod.application.async_ import CommandPort, QueryPort
```

### UseCase

```python
class UseCase(BaseOperation)
```

Base class for synchronous application use cases.

#### Constructor

`UseCase(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `uow` | `UnitOfWork` | Unit of work for transaction management. Default: `NullUnitOfWork`. |
| `logger` | `Logger \| AsyncLogger` | Logger instance. Default: `NullLogger`. |
| `event_bus` | `EventBus \| AsyncEventBus` | Event bus instance. Default: `NullEventBus`. |
| `cache` | `Cache \| AsyncCache` | Cache instance. Default: `NullCache`. |
| `**ports` | `Port` | Additional port dependencies. |

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `uow` | `UnitOfWork` | `NullUnitOfWork()` | Transactional unit of work. |
| `events` | `list[Event]` | `[]` | Events collected during the last `run()` call. `init=False`. |
| `logger` | `Logger \| AsyncLogger` | `NullLogger()` | Logger. |
| `event_bus` | `EventBus \| AsyncEventBus` | `NullEventBus()` | Event bus. |
| `cache` | `Cache \| AsyncCache` | `NullCache()` | Cache. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `run` | `abstractmethod run(self, *args, **kwargs) -> Any` | Execute the use case. Auto-wrapped with `EventCollector`, transaction, logging, and event publishing. |

#### Auto-Wrapping Behavior

When `run()` is called:

1. `uow.begin()` starts a transaction.
2. Events are collected via `EventCollector` during execution.
3. On success: `uow.commit()`, events logged, cache flushed, events published on event bus.
4. On failure: `uow.rollback()`, exception logged, exception re-raised.
5. If commit fails: `uow.rollback()`, commit failure logged, exception re-raised.

#### Field Validation

- Fields must be `Port` subclasses.
- Recommended field types: `Commandport[TCommand]` and `QueryPort[TQuery]`.
- `Session` and `AsyncSession` are not allowed (raise `InvalidUseCasePortFieldError`).
- `BaseHandler` and `AsyncBaseHandler` are also rejected.

### AsyncUseCase

```python
class AsyncUseCase(BaseOperation)
```

#### Constructor

`AsyncUseCase(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `uow` | `UnitOfWork \| AsyncUnitOfWork` | Unit of work. Default: `NullUnitOfWork`. |
| `logger` | `Logger \| AsyncLogger` | Logger. Default: `NullLogger`. |
| `event_bus` | `EventBus \| AsyncEventBus` | Event bus. Default: `NullEventBus`. |
| `cache` | `Cache \| AsyncCache` | Cache. Default: `NullCache`. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `run` | `abstractmethod async run(self, *args, **kwargs) -> Any` | Async execute the use case. Same auto-wrapping as sync but uses `should_await` for all port calls. |

### Port

```python
class Port(BaseGuarded)
```

Abstract base class for defining dependency interfaces.

- No constructor parameters.
- Subclasses declare abstract methods and fields.
- Public methods are auto-wrapped with mutation context.

### CommandPort

```python
class CommandPort(HandlerProtocol, Generic[TCommand])
```

Application-layer handler port for write operations. UseCases declare `CommandPort[Command]` as fields.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `handle` | `abstractmethod handle(self, command: TCommand) -> TResult` | Execute the command. |

#### Type Parameters

| Parameter | Constraint | Description |
|-----------|------------|-------------|
| `TCommand` | Must be a `Command` subclass | The command type this port handles. |

Infrastructure provides concrete implementations via `CommandHandler[C]`.

### QueryPort

```python
class QueryPort(HandlerProtocol, Generic[TQuery])
```

Application-layer handler port for read operations. UseCases declare `QueryPort[Query]` as fields.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `handle` | `abstractmethod handle(self, query: TQuery) -> TResult` | Execute the query. |

#### Type Parameters

| Parameter | Constraint | Description |
|-----------|------------|-------------|
| `TQuery` | Must be a `Query` subclass | The query type this port handles. |

Infrastructure provides concrete implementations via `QueryHandler[Q]`.

### Logger

```python
class Logger(Port)
```

Synchronous logging port.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `debug` | `abstractmethod debug(self, msg: str, **context: object)` | Log at debug level. |
| `info` | `abstractmethod info(self, msg: str, **context: object)` | Log at info level. |
| `warning` | `abstractmethod warning(self, msg: str, **context: object)` | Log at warning level. |
| `error` | `abstractmethod error(self, msg: str, **context: object)` | Log at error level. |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `msg` | `str` | The log message. |
| `**context` | `object` | Additional structured context. |

### AsyncLogger

```python
from aod.application.async_ import Logger
```

Same interface as `Logger` but all methods are `async`.

### EventBus

```python
class EventBus(Port)
```

Synchronous event publishing port.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `publish` | `abstractmethod publish(self, *events: Event)` | Publish one or more domain events. |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `*events` | `Event` | Domain events to publish. |

### AsyncEventBus

```python
from aod.application.async_ import EventBus
```

Same interface but `publish` is async.

### UnitOfWork

```python
class UnitOfWork(Port)
```

Synchronous unit of work for transaction management.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `begin` | `abstractmethod begin(self)` | Start a new transaction. |
| `commit` | `abstractmethod commit(self)` | Commit the current transaction. |
| `rollback` | `abstractmethod rollback(self)` | Roll back the current transaction. |

### AsyncUnitOfWork

```python
from aod.application.async_ import UnitOfWork
```

Same interface but all methods are async.

### Cache

```python
class Cache(Port)
```

Synchronous cache port.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get` | `abstractmethod get(self, key: str) -> Any` | Retrieve a value by key. |
| `set` | `abstractmethod set(self, key: str, value: Any, ttl: float \| None = None)` | Store a value with optional TTL. |
| `delete` | `abstractmethod delete(self, key: str)` | Remove a value by key. |
| `flush` | `abstractmethod flush(self)` | Clear all cached values. |
| `set_promise` | `abstractmethod set_promise(self, key: str, value: Any, ttl: float \| None = None)` | Deferred set — value will be set at a later time. |
| `delete_promise` | `abstractmethod delete_promise(self, key: str)` | Deferred delete — value will be deleted at a later time. |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Cache key. |
| `value` | `Any` | Value to cache. |
| `ttl` | `float \| None` | Time-to-live in seconds. `None` means no expiry. |

### AsyncCache

```python
from aod.application.async_ import Cache
```

Same interface but `get`, `set`, `delete`, and `flush` are async. `set_promise` and `delete_promise` remain sync.

### Command

```python
class Command(BaseSealed, Generic[TEntity, TResult])
```

Immutable command contract for write operations.

#### Constructor

`Command(**fields)`

#### Type Parameters

| Parameter | Constraint | Description |
|-----------|------------|-------------|
| `TEntity` | Must be `RootEntity` subclass | The aggregate root this command targets. |
| `TResult` | Any | The result type. |

#### Constraints

- Fields cannot reference non-root `Entity` types (even inside `list[Entity]`, `Optional[Entity]`, etc.).
- The generic `TEntity` argument is validated to be a `RootEntity` subclass at class creation time.

### Query

```python
class Query(BaseSealed, Generic[TEntity, TResult])
```

Immutable query contract for read operations.

#### Constructor

`Query(**fields)`

#### Type Parameters

| Parameter | Constraint | Description |
|-----------|------------|-------------|
| `TEntity` | Must be `RootEntity` subclass | The aggregate root this query targets. |
| `TResult` | Must contain a `RootEntity` | The result type must include at least one `RootEntity` (e.g. `User`, `list[User]`, `tuple[int, User \| None]`). |

#### Constraints

- Same field restrictions as `Command`.
- `TResult` is validated to contain at least one `RootEntity` type.

---

## Infrastructure Layer

```python
from aod.infrastructure import Session, AsyncSession
from aod.infrastructure import ReadModel, WriteModel
from aod.infrastructure import ReadProjection, WriteProjection, Projection
from aod.infrastructure import AsyncReadProjection, AsyncWriteProjection, AsyncProjection
from aod.infrastructure import CommandHandler, QueryHandler
from aod.infrastructure import AsyncCommandHandler, AsyncQueryHandler
from aod.infrastructure import AdapterContainer
from aod.infrastructure import InfrastructureException
```

### Session

```python
class Session(Port)
```

Synchronous database session abstraction.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `execute` | `abstractmethod execute(self, operation: object) -> object` | Execute a write operation. |
| `query` | `abstractmethod query(self, operation: object) -> object` | Execute a read operation. |
| `begin` | `abstractmethod begin(self) -> None` | Start a new transaction. |
| `commit` | `abstractmethod commit(self) -> None` | Commit the transaction. Wrapped to raise `CommitOutsideUnitOfWorkError` if no `_CommitContext`. |
| `rollback` | `abstractmethod rollback(self) -> None` | Roll back the transaction. |
| `close` | `abstractmethod close(self) -> None` | Release resources. |
| `is_dirty` | `abstractmethod is_dirty(self) -> bool` | Check for uncommitted changes. |

### AsyncSession

```python
class AsyncSession(Port)
```

Same interface as `Session` but `execute`, `query`, `begin`, `commit`, `rollback`, `close` are async. `is_dirty()` is sync.

### ReadModel

```python
class ReadModel(BaseSealed)
```

Immutable input model for read projections.

#### Constructor

`ReadModel(**fields)` — All fields are keyword-only.

### WriteModel

```python
class WriteModel(BaseSealed)
```

Immutable input model for write projections.

#### Constructor

`WriteModel(**fields)` — All fields are keyword-only.

### ReadProjection

```python
class ReadProjection(ReadProjectionBase)
```

Synchronous read projection.

#### Constructor

`ReadProjection(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `session` | `Session \| None` | Optional database session. Default: `None`. |
| `**ports` | `Port` | Port dependencies. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `read` | `abstractmethod read(self, model: ReadModel) -> Any` | Execute read logic. Auto-wrapped with event collection, logging, cache flush, and event bus publish. |

### WriteProjection

```python
class WriteProjection(WriteProjectionBase)
```

Synchronous write projection.

#### Constructor

`WriteProjection(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `session` | `Session \| None` | Optional database session. Default: `None`. |
| `**ports` | `Port` | Port dependencies. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `write` | `abstractmethod write(self, model: WriteModel) -> Any` | Execute write logic. Auto-wrapped with `CommitContext`, transaction begin, event collection, rollback on failure, logging, cache flush, and event bus publish. |

### Projection

```python
class Projection(ReadProjection, WriteProjection)
```

Combined read and write projection.

#### Constructor

Same as `ReadProjection` and `WriteProjection`.

#### Methods

Both `read(self, model: ReadModel) -> Any` and `write(self, model: WriteModel) -> Any`.

### AsyncReadProjection

```python
class AsyncReadProjection(AsyncReadProjectionBase)
```

#### Constructor

`AsyncReadProjection(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `session` | `Session \| AsyncSession \| None` | Optional session. Default: `None`. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `read` | `abstractmethod async read(self, model: ReadModel) -> Any` | Async read. |

### AsyncWriteProjection

```python
class AsyncWriteProjection(AsyncWriteProjectionBase)
```

#### Constructor

`AsyncWriteProjection(**fields)` — `session: Session | AsyncSession | None = None`.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `write` | `abstractmethod async write(self, model: WriteModel) -> Any` | Async write. |

### AsyncProjection

```python
class AsyncProjection(AsyncReadProjection, AsyncWriteProjection)
```

Combined async read and write projection. Both `read` and `write` are async.

### CommandHandler

```python
class CommandHandler(BaseHandler, AppCommandHandler, Generic[TCommand])
```

Synchronous command handler for a specific command type.

#### Constructor

`CommandHandler(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `session` | `Session \| None` | Optional session. Default: `None`. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `handle` | `abstractmethod handle(self, command: TCommand) -> object` | Handle a command. Returns an implementation-specific result. |

### QueryHandler

```python
class QueryHandler(BaseHandler, AppQueryHandler, Generic[TQuery])
```

Synchronous query handler for a specific query type.

#### Constructor

`QueryHandler(**fields)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `session` | `Session \| None` | Optional session. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `handle` | `abstractmethod handle(self, query: TQuery) -> object` | Handle a query. |

### AsyncCommandHandler

```python
class AsyncCommandHandler(AsyncBaseHandler, AppAsyncCommandHandler, Generic[TCommand])
```

#### Constructor

`AsyncCommandHandler(**fields)` — `session: AsyncSession | None = None`.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `handle` | `abstractmethod async handle(self, command: TCommand) -> object` | Async handle a command. |

### AsyncQueryHandler

```python
class AsyncQueryHandler(AsyncBaseHandler, AppAsyncQueryHandler, Generic[TQuery])
```

#### Constructor

`AsyncQueryHandler(**fields)` — `session: AsyncSession | None = None`.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `handle` | `abstractmethod async handle(self, query: TQuery) -> object` | Async handle a query. |

### AdapterContainer

```python
class AdapterContainer(BaseBehaviour)
```

Dependency injection container.

#### Constructor

`AdapterContainer(**fields)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sessions` | `set[type[Session] \| type[AsyncSession]]` | `set()` | Session classes to manage. |
| `handlers` | `list[type[CommandHandler \| QueryHandler \| AsyncCommandHandler \| AsyncQueryHandler]]` | `[]` | Handler classes to register. |
| `logger` | `Logger \| AsyncLogger` | `NullLogger()` | Logger instance. |
| `event_bus` | `EventBus \| AsyncEventBus` | `NullEventBus()` | Event bus instance. |
| `cache` | `Cache \| AsyncCache` | `NullCache()` | Cache instance. |
| `_sessions_needed` | `dict` | `{}` | Private cache of instantiated sessions. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_session` | `get_session(self, session_cls: type) -> Session \| AsyncSession` | Retrieve or instantiate a session. Raises `SessionNotFoundError`. |
| `get_handler` | `get_handler(self, contract: type[Command \| Query]) -> handler` | Find handler by command/query type. Raises `HandlerNotFoundError`. |
| `get_uow` | `get_uow(self) -> UnitOfWork \| AsyncUnitOfWork` | Create a UoW with all instantiated sessions. |
| `get_port` | `get_port(self, port: type[Port]) -> Port` | Find port by type. Raises `PortNotFoundError`. |
| `with_adapters` | `with_adapters(self, **overrides) -> Self` | Create a copy with overridden fields. |
| `adapt_use_case` | `adapt_use_case(self, use_case_cls, **overrides) -> UseCase \| AsyncUseCase` | Create a use case with all dependencies wired. |
| `adapt_projection` | `adapt_projection(self, projection_cls, **overrides) -> ProjectionBase` | Create a projection with all dependencies wired. |

---

## Testing Layer

```python
from aod.testing import build, events_of, assert_event_emitted, assert_no_events, check_invariant
from aod.testing import FakeDomain
from aod.testing.doubles import (
    SpyLogger, SpyEventBus, SpyCache, SpySession, SpyAsyncSession,
    port_stub, spy_adapter_container,
)
from aod.testing.doubles.application.async_ import SpyLogger, SpyEventBus, SpyCache
```

### build

```
build(cls: type[T], **kwargs: Any) -> T
```

Create domain object skipping validation.

| Parameter | Type | Description |
|-----------|------|-------------|
| `cls` | `type[T]` | The class to instantiate. |
| `**kwargs` | `Any` | Field values. |

### events_of

```
events_of(obj: BaseGuarded) -> list[Event]
```

Extract events from a domain object.

| Parameter | Type | Description |
|-----------|------|-------------|
| `obj` | `BaseGuarded` | Entity, ValueObject, or Service. |

### assert_event_emitted

```
assert_event_emitted(events: Sequence[Event], event_type: type[Event], **attrs: Any) -> Event
```

Assert a specific event was emitted.

| Parameter | Type | Description |
|-----------|------|-------------|
| `events` | `Sequence[Event]` | Events list from `events_of()`. |
| `event_type` | `type[Event]` | Expected event class. |
| `**attrs` | `Any` | Field values to match. |

### assert_no_events

```
assert_no_events(events: Sequence[Event]) -> None
```

Assert no events were emitted.

| Parameter | Type | Description |
|-----------|------|-------------|
| `events` | `Sequence[Event]` | Events list to check. |

### check_invariant

```
check_invariant(cls: type, invariant_name: str, data: dict[str, Any] | None = None, **kwargs: Any) -> None
```

Run a single invariant validator.

| Parameter | Type | Description |
|-----------|------|-------------|
| `cls` | `type` | Class defining the invariant. |
| `invariant_name` | `str` | Name of the validator. |
| `data` | `dict[str, Any] \| None` | Field values. |
| `**kwargs` | `Any` | Additional field values. |

### FakeDomain

```
FakeDomain(model_cls: type[T], **defaults: Any)
```

Factory for domain objects with auto-generated data.

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_cls` | `type[T]` | Entity, RootEntity, or ValueObject class. |
| `**defaults` | `Any` | Default field values. |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `__call__` | `__call__(self, **overrides) -> T` | Build an instance with auto-generated fields for unfilled ones. |
| `batch` | `batch(self, count, overrides_list=None) -> list[T]` | Build multiple instances. |

### SpyLogger

| Property | Type | Description |
|----------|------|-------------|
| `entries` | `list[LogEntry]` | All logged entries. `LogEntry` has `.level`, `.msg`, `.context`. |

Methods: `debug(msg, **context)`, `info(msg, **context)`, `warning(msg, **context)`, `error(msg, **context)`.

### SpyEventBus

| Property | Type | Description |
|----------|------|-------------|
| `published` | `list[Event]` | All published events. |

Method: `publish(*events)`.

### SpyCache

| Properties | Type | Description |
|------------|------|-------------|
| `get_calls` | `list[str]` | Keys passed to `get()`. |
| `set_calls` | `list[tuple]` | Arguments passed to `set()`. |
| `delete_calls` | `list[str]` | Keys passed to `delete()`. |
| `flush_calls` | `list[None]` | Flush call records. |

Methods: `get(key)`, `set(key, value, ttl=None)`, `delete(key)`, `flush()`, `set_promise(key, value, ttl=None)`, `delete_promise(key)`.

### SpySession / SpyAsyncSession

Each required lifecycle method records calls and lets you configure return values:

| Property | Type | Description |
|----------|------|-------------|
| `begin` | stub | Use `.called`, `.calls`, `.returns()`, `.always_returns()` |
| `commit` | stub | Use `.called`, `.calls`, `.returns()`, `.always_returns()` |
| `rollback` | stub | Use `.called`, `.calls`, `.returns()`, `.always_returns()` |
| `close` | stub | Use `.called`, `.calls`, `.returns()`, `.always_returns()` |
| `is_dirty` | stub | Pre-configured to `returns(False)`. Use `.returns()`, `.always_returns()` |

SpyAsyncSession mirrors SpySession with async lifecycle methods.

### Async Spy Classes

```python
from aod.testing.doubles.application.async_ import SpyLogger, SpyEventBus, SpyCache
```

Same names as sync variants. All methods that perform I/O are async.

### `spy_adapter_container`

```
spy_adapter_container(container: AdapterContainer) -> AdapterContainer
```

Create a version of a container where sessions and ports are replaced with stubs.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_session_stub` | `get_session_stub(session_cls) -> Any` | Returns a stub for the given session class |
| `get_port_stub` | `get_port_stub(port_cls) -> Any` | Returns a stub for the given port class |
| `get_handler` | `get_handler(contract) -> Any` | Returns the handler for a contract (handle is a stub) |

### `port_stub`

```
port_stub(port_cls: type[Port]) -> type
```

Create a stub class from any `Port` subclass. Every public method records calls and lets you configure return values.

### Stub Control

Every stub method provides:

| Property / Method | Description |
|-------------------|-------------|
| `.returns(*values)` | Set sequential return values |
| `.always_returns(value)` | Set a constant return value |
| `.called` | Whether the method was called |
| `.call_count` | Number of calls |
| `.calls` | List of argument lists per call |

---

## Exceptions

```python
from aod.exceptions import (
    DomainException, MutationForbiddenException, InvarianceException,
    InvalidEntityTypeError, InvalidRootEntityTypeError, InvalidNestedTypeError,
    InvalidServiceParameterError, DuplicateDomainTypeError, ModelValidationError,
    ClassExpectedError, InvalidCommandFieldTypeError, InvalidQueryResultTypeError,
    InvalidGenericTypeArgError, InvalidServiceTypeError,
    ApplicationException, UnresolvableEntityError, CommitOutsideUnitOfWorkError,
    InvalidUseCasePortFieldError,
    InfrastructureException, HandlerResultTypeError, HandlerModelError,
    PortNotFoundError, SessionNotFoundError, InvalidPortFieldError,
    DuplicateHandlerError, HandlerNotFoundError,
)
```

### DomainException Hierarchy

| Exception | Parent | Description |
|-----------|--------|-------------|
| `DomainException` | `Exception` | Base for all domain errors. |
| `MutationForbiddenException` | `DomainException` | Mutation attempted outside allowed context. |
| `InvarianceException` | `DomainException`, `ValueError` | Field/model invariance violated. |
| `InvalidEntityTypeError` | `DomainException` | Not an `Entity` subclass. |
| `InvalidRootEntityTypeError` | `DomainException` | `Entity` but not `RootEntity`. |
| `InvalidNestedTypeError` | `DomainException` | Entity field references forbidden domain type. |
| `InvalidServiceParameterError` | `DomainException` | Service param/return type has disallowed type. |
| `DuplicateDomainTypeError` | `DomainException` | Type registered in multiple contexts. |
| `ModelValidationError` | `DomainException` | Pydantic validation failed. Wraps `ValidationError`. |
| `ClassExpectedError` | `DomainException` | Instance given where class required. |
| `InvalidCommandFieldTypeError` | `DomainException` | Command/Query field references non-root Entity. |
| `InvalidQueryResultTypeError` | `DomainException` | Query TResult does not include a RootEntity. |
| `InvalidGenericTypeArgError` | `DomainException` | Generic argument fails its constraint. |
| `InvalidServiceTypeError` | `DomainException` | Not a `Service` subclass. |

### ApplicationException Hierarchy

| Exception | Parent | Description |
|-----------|--------|-------------|
| `ApplicationException` | `Exception` | Base for application errors. |
| `UnresolvableEntityError` | `ApplicationException` | Cannot determine RootEntity from Command/Query. |
| `CommitOutsideUnitOfWorkError` | `ApplicationException` | Commit outside a UoW context. |
| `InvalidUseCasePortFieldError` | `ApplicationException` | UseCase field is not a Port subclass. |

### InfrastructureException Hierarchy

| Exception | Parent | Description |
|-----------|--------|-------------|
| `InfrastructureException` | `Exception` | Base for infrastructure errors. |
| `HandlerResultTypeError` | `InfrastructureException` | Handler returned wrong type. |
| `HandlerModelError` | `InfrastructureException` | Handler missing required field. |
| `PortNotFoundError` | `InfrastructureException` | No port of requested type registered. |
| `SessionNotFoundError` | `InfrastructureException` | No session of requested type registered. |
| `InvalidPortFieldError` | `InfrastructureException` | Field on container is not a Port type. |
| `DuplicateHandlerError` | `InfrastructureException` | Duplicate handler for same contract. |
| `HandlerNotFoundError` | `InfrastructureException` | No handler for given contract. |

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="../infrastructure/sessions.md">Sessions</a></h3>
<p>Database abstraction</p>
</div>

<div class="feature-card">
<h3><a href="../infrastructure/projections.md">Projections</a></h3>
<p>Read/write data efficiently</p>
</div>

<div class="feature-card">
<h3><a href="../infrastructure/container.md">Container</a></h3>
<p>Dependency injection</p>
</div>

<div class="feature-card">
<h3><a href="../testing/index.md">Testing Utilities</a></h3>
<p>Testing with spies</p>
</div>

</div>