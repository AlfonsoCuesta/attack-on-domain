# Exception Hierarchy

All framework exceptions are exported from `aod.exceptions`.

## Exception Tree

```
Exception
├── DomainException                         # Base: domain rule violations
│   ├── MutationForbiddenException          # Mutation outside allowed context
│   ├── InvalidEntityTypeError              # Not an Entity subclass
│   ├── InvalidRootEntityTypeError          # Entity but not RootEntity
│   ├── InvalidServiceTypeError             # Not a Service subclass
│   ├── ClassExpectedError                  # Instance given where class required
│   ├── InvalidNestedTypeError              # Entity field references forbidden type
│   ├── InvalidServiceParameterError        # Service method param has disallowed type
│   ├── DuplicateDomainTypeError            # Domain type in >1 BoundedContext
│   ├── InvarianceException (also ValueError)  # Field/model invariance violated
│   │
│   │   # Class-creation time (Command/Query/Projection validation)
│   ├── InvalidCommandFieldTypeError        # Command/Query field has non-root Entity
│   ├── InvalidQueryResultTypeError         # Query TResult has no RootEntity
│   ├── InvalidGenericTypeArgError          # Generic arg fails constraint
│   ├── InvalidProjectionTypeError          # Projection type not ReadModel or None
│   │
│   │   # Construction time (Pydantic validation wrapper)
│   └── ModelValidationError                # Pydantic validation failed during model construction
│
├── ApplicationException                    # Base: application layer errors
│   ├── UnresolvableEntityError             # Cannot determine RootEntity from Command/Query
│   └── CommitOutsideUnitOfWorkError        # Commit outside UnitOfWork context
│
└── InfrastructureException                # Base: infrastructure layer errors
    ├── UnresolvableProjectionTypeError     # Cannot determine projection type from handler
    ├── DuplicateProjectionHandlerError     # Duplicate handler in ProjectionStore
    ├── ProjectionHandlerNotFoundError      # No handler for projection type
    ├── DuplicateHandlerError               # Duplicate handler for Command/Query
    ├── HandlerNotFoundError                # No handler for Command/Query
    └── HandlerResultTypeError              # Handler returned wrong type
```

## When Each Exception Is Raised

### Class‑Creation Time (DomainException subclasses)

| Exception | Trigger |
|---|---|
| `InvalidEntityTypeError` | A type passed to `BoundedContext(aggregate_roots=[...])` is not an `Entity` subclass |
| `InvalidRootEntityTypeError` | A type is `Entity` but not `RootEntity` |
| `InvalidServiceTypeError` | A type passed to `BoundedContext(services=[...])` is not a `Service` subclass |
| `InvalidNestedTypeError` | An Entity field references a type not allowed in Entity fields |
| `InvalidServiceParameterError` | A Service method parameter/return has a non-root `Entity` |
| `InvalidCommandFieldTypeError` | A `Command` or `Query` field references a non-root `Entity` (e.g. `items: list[Entity]`) |
| `InvalidQueryResultTypeError` | `Query[TEntity, TResult]` where `TResult` does not include any `RootEntity` |
| `InvalidGenericTypeArgError` | A generic argument (e.g. `TEntity` in `Command[str, int]`) does not satisfy its constraint |
| `InvalidProjectionTypeError` | `ProjectionQuery[T]` or `ProjectionCommand[T]` where `T` is not `ReadModel`, `None`, or a `ReadModel` subclass |
| `DuplicateDomainTypeError` | Same domain type registered in >1 `BoundedContext` |

### Handler Wiring Time (DomainException subclasses)

| Exception | Trigger |
|---|---|
| `HandlerTypeMismatchError` | A `QueryHandler` passed to `command_handlers` (or vice‑versa), or a handler that doesn't extend the expected base |
| `HandlerEntityMismatchError` | `Repository[User]` receives a handler that handles `Order` |
| `UnresolvableHandlerTypeError` | A handler's generic bases don't contain a recognizable `Command`/`Query` type |

### Runtime — Handler Dispatch (InfrastructureException subclasses)

| Exception | Trigger |
|---|---|
| `DuplicateHandlerError` | Two handlers registered for the same `Command`/`Query` type |
| `HandlerNotFoundError` | No handler found for a given `Command`/`Query` type |
| `HandlerResultTypeError` | `handler.handle()` returned a value that doesn't match the expected return type |

### Runtime — ProjectionStore Dispatch (InfrastructureException subclasses)

| Exception | Trigger |
|---|---|
| `UnresolvableProjectionTypeError` | A projection handler's generic bases don't contain a recognizable projection type |
| `DuplicateProjectionHandlerError` | Two handlers registered for the same projection type in a `ProjectionStore` |
| `ProjectionHandlerNotFoundError` | `store.query()` or `store.command()` called with a type that has no handler |

### Runtime — UnitOfWork (ApplicationException subclasses)

| Exception | Trigger |
|---|---|
| `ProjectionStoreNotConfiguredError` | UoW receives a `ProjectionQuery`/`ProjectionCommand` but no `projection_store` was provided |
| `UnresolvableEntityError` | UoW cannot determine which `RootEntity` a `Command`/`Query` targets |
| `CommitOutsideUnitOfWorkError` | `commit()` called outside a `UnitOfWork` context |

### Runtime — General

| Exception | Trigger |
|---|---|
| `MutationForbiddenException` | Setting/deleting an attribute on an object that is in a blocked mutation state |
| `InvarianceException` | A `@field_invariance` or `@invariance` validator failed |

### Construction Time — Model Validation

| Exception | Trigger |
|---|---|
| `ModelValidationError` | Pydantic validation failed during `__init__` (e.g. missing required field, wrong type). If the cause is an `InvarianceException`, that exception is re-raised directly instead. |

## Catching Pattern

```python
from aod.exceptions import (
    ApplicationException,
    DomainException,
    InfrastructureException,
)

try:
    uow.command(some_command)
except InfrastructureException:
    # Catch-all for infrastructure errors
    ...
except ApplicationException:
    # Catch-all for application errors
    ...
except DomainException:
    # Catch-all for domain rule violations
    ...
```
