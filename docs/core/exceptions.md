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
│   │   # Class-creation time (Command/Query validation)
│   ├── InvalidCommandFieldTypeError        # Command/Query field has non-root Entity
│   ├── InvalidQueryResultTypeError         # Query TResult has no RootEntity
│   ├── InvalidGenericTypeArgError          # Generic arg fails constraint
│   │
│   │   # Construction time (Pydantic validation wrapper)
│   └── ModelValidationError                # Pydantic validation failed during model construction
│
├── ApplicationException                    # Base: application layer errors
│   ├── UnresolvableEntityError             # Cannot determine RootEntity from Command/Query
│   └── CommitOutsideUnitOfWorkError        # Commit outside UnitOfWork context
│
└── InfrastructureException                # Base: infrastructure layer errors
    ├── HandlerModelError                   # Handler missing required field
    ├── DuplicateHandlerError               # Duplicate handler for Command/Query
    ├── HandlerNotFoundError                # No handler for Command/Query
    ├── HandlerResultTypeError              # Handler returned wrong type
    ├── InvalidPortFieldError               # Container field not a Port subclass
    ├── PortNotFoundError                   # No port of requested type registered
    └── SessionNotFoundError                # No session of requested type registered
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
| `DuplicateDomainTypeError` | Same domain type registered in >1 `BoundedContext` |

### Runtime — Handler Dispatch (InfrastructureException subclasses)

| Exception | Trigger |
|---|---|
| `HandlerModelError` | A handler's `handle` method or class is missing a required field |
| `DuplicateHandlerError` | Two handlers registered for the same `Command`/`Query` type |
| `HandlerNotFoundError` | No handler found for a given `Command`/`Query` type |
| `HandlerResultTypeError` | `handler.handle()` returned a value that doesn't match the expected return type |

### Runtime — Container (InfrastructureException subclasses)

| Exception | Trigger |
|---|---|
| `InvalidPortFieldError` | An `AdapterContainerBase` subclass field is not a `Port` subclass |
| `PortNotFoundError` | `get_port()` called for a port type not registered on the container |
| `SessionNotFoundError` | `get_handler()` cannot find a session of the required type |

### Runtime — UnitOfWork (ApplicationException subclasses)

| Exception | Trigger |
|---|---|
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