# Handlers

Handlers process commands and queries. They bridge the gap between the application and infrastructure layers, implementing `CommandPort[T]` and `QueryPort[T]` from the application layer.

UseCases declare `CommandPort[Command]` / `QueryPort[Query]` as fields; infrastructure handlers provide the concrete implementation that is injected by the container.

## Import

```python
from aod.infrastructure import CommandHandler, QueryHandler
```

For async operations:

```python
from aod.infrastructure import AsyncCommandHandler, AsyncQueryHandler
```

## Basic Usage

Subclass `CommandHandler` or `QueryHandler` parameterized by your contract type, and implement the `handle()` method:

```python
from aod.infrastructure import CommandHandler, QueryHandler, Session


class PostgresSession(Session):
    def execute(self, operation: object) -> None: ...
    def query(self, operation: object) -> object: ...


class CreateUserHandler(CommandHandler[CreateUser]):
    session: PostgresSession

    def handle(self, command: CreateUser) -> None:
        user = User(id=command.user_id, name=command.name, email=command.email)
        self.session.execute(user)

class GetUserHandler(QueryHandler[GetUser]):
    session: PostgresSession

    def handle(self, query: GetUser) -> User | None:
        return self.session.query(f"SELECT * FROM users WHERE id = {query.user_id}")
```

## Class Reference

### `BaseHandler`

Base class for all handlers. Provides mutation-guarded behaviour. Has **no** intrinsic `session` field — subclasses declare their own session fields with concrete types.

**Constructor parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `**fields` | Any | Fields declared on the handler subclass (e.g. `session=PostgresSession()`) |

### `AsyncBaseHandler`

Async variant of `BaseHandler`. Same as `BaseHandler` — no inherited session field. Subclasses declare their own.

### `CommandHandler[TCommand]`

Sync command handler. Inherits from `BaseHandler`, `AppCommandHandler` (which is `HandlerProtocol(Port)`), and `Generic[TCommand]`.

**Type Parameters:**

| Parameter | Constraint | Description |
|-----------|------------|-------------|
| `TCommand` | Must be a `Command` subclass | The command type this handler processes |

#### `handle(self, command: TCommand) -> object`

Abstract method. Implement to process a command.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `command` | `TCommand` | The command instance to process |

**Returns:** Any object. The return type is validated at runtime against the handler's generic parameter.

### `QueryHandler[TQuery]`

Sync query handler. Inherits from `BaseHandler`, `AppQueryHandler` (which is `HandlerProtocol(Port)`), and `Generic[TQuery]`.

**Type Parameters:**

| Parameter | Constraint | Description |
|-----------|------------|-------------|
| `TQuery` | Must be a `Query` subclass | The query type this handler processes |

#### `handle(self, query: TQuery) -> object`

Abstract method. Implement to process a query.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `TQuery` | The query instance to process |

**Returns:** Any object. The return type is validated at runtime against the query's `TResult`.

### `AsyncCommandHandler[TCommand]`

Async command handler. Inherits from `AsyncBaseHandler`, `AppAsyncCommandHandler` (which is `HandlerProtocol(Port)`), and `Generic[TCommand]`.

#### `async handle(self, command: TCommand) -> object`

Async abstract method. Implement to process a command asynchronously.

### `AsyncQueryHandler[TQuery]`

Async query handler. Inherits from `AsyncBaseHandler`, `AppAsyncQueryHandler` (which is `HandlerProtocol(Port)`), and `Generic[TQuery]`.

#### `async handle(self, query: TQuery) -> object`

Async abstract method. Implement to process a query asynchronously.

## Generic Type Binding

Handlers are generic over their contract type. The generic argument is used at runtime for return type validation:

```python
class CreateUserHandler(CommandHandler[CreateUser]):
    session: PostgresSession

    def handle(self, command: CreateUser) -> None:
        pass  # This handler only accepts CreateUser commands
```

## Session Field

Handlers include a `session` field for database access:

```python
class CreateUserHandler(CommandHandler[CreateUser]):
    session: PostgresSession  # Injected by the container

    def handle(self, command: CreateUser) -> None:
        self.session.execute(...)
```

## Return Type Validation

Handler return types are validated at runtime via `_wrap_handle()`. If the return value does not match the expected type (derived from the generic parameter), `HandlerResultTypeError` is raised:

```python
from aod.infrastructure import QueryHandler

class GetUserHandler(QueryHandler[GetUser]):
    session: PostgresSession

    def handle(self, query: GetUser) -> User | None:
        return self.session.query(...)  # Must return User | None
```

## Async Handlers

```python
from aod.infrastructure import AsyncCommandHandler, AsyncQueryHandler, AsyncSession

class AsyncPostgresSession(AsyncSession):
    async def execute(self, operation: object) -> None: ...
    async def query(self, operation: object) -> object: ...


class AsyncCreateUserHandler(AsyncCommandHandler[CreateUser]):
    session: AsyncPostgresSession

    async def handle(self, command: CreateUser) -> None:
        user = User(id=command.user_id, name=command.name)
        await self.session.execute(user)

class AsyncGetUserHandler(AsyncQueryHandler[GetUser]):
    session: AsyncPostgresSession

    async def handle(self, query: GetUser) -> User | None:
        return await self.session.query(...)
```

## Handler Registration

Handlers are registered in `AdapterContainer`:

```python
from aod.infrastructure import AdapterContainer

container = AdapterContainer(sessions={PostgresSession}, handlers=[CreateUserHandler, GetUserHandler])
```

## Handler Discovery

The container discovers and instantiates handlers by contract type:

```python
container = AdapterContainer()
handler = container.get_handler(CreateUser)  # Returns CreateUserHandler instance
result = handler.handle(CreateUser(...))
```

## Testing

Use `SpySession` for handler testing:

```python
from aod.testing.doubles import SpySession

session = SpySession()
handler = CreateUserHandler(session=session)

handler.handle(CreateUser(user_id="1", name="Alice"))

assert handler.handle.called
```

## Common Patterns

### Command Handler

```python
class PlaceOrderHandler(CommandHandler[PlaceOrder]):
    session: PostgresSession

    def handle(self, command: PlaceOrder) -> None:
        order = Order(id=command.order_id, total=command.total)
        self.session.execute(order)
```

### Query Handler

```python
class GetUserHandler(QueryHandler[GetUser]):
    session: PostgresSession

    def handle(self, query: GetUser) -> User | None:
        return self.session.query(f"SELECT * FROM users WHERE id = {query.user_id}")
```

### Handler with Validation

Validation belongs in the domain, not the handler. The handler delegates to domain objects that enforce their own constraints:

```python
class CreateUserHandler(CommandHandler[CreateUser]):
    session: PostgresSession

    def handle(self, command: CreateUser) -> None:
        user = User(id=command.user_id, name=command.name, email=command.email)
        self.session.execute(user)
```

### Handler with Multiple Dependencies

```python
class CreateUserHandler(CommandHandler[CreateUser]):
    session: PostgresSession
    validator: UserValidator

    def handle(self, command: CreateUser) -> None:
        self.validator.validate(command)
        user = User(id=command.user_id, name=command.name)
        self.session.execute(user)
```

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="../application/use-cases.md">UseCase</a></h3>
<p>Learn how use cases orchestrate domain logic</p>
</div>

<div class="feature-card">
<h3><a href="../application/contracts.md">Contracts</a></h3>
<p>Learn about commands and queries</p>
</div>

<div class="feature-card">
<h3><a href="container.md">Container</a></h3>
<p>Learn about handler registration</p>
</div>


</div>