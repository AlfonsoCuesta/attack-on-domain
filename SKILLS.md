# attack-on-domain — Skills

Specialized instructions for common tasks.

## Adding New Domain Types

1. Create `ValueObject` for immutable data (identifiers, addresses, etc.)
2. Create `Entity` for mutable objects with identity
3. Create `RootEntity` as aggregate roots
4. Create `Service` for stateless operations
5. Add to `BoundedContext` via `aggregate_roots`, `services`, or let `discover_types` find them

```python
from aod.domain import RootEntity, ValueObject, Entity, Service

class OrderId(ValueObject):
    value: str

class Order(RootEntity):
    id: OrderId
    total: float = 0.0

class PricingService(Service):
    def calculate_total(self, base: float) -> float:
        return base * 1.1
```

## Adding New Use Cases

1. Create `Command` or `Query` (both extend `BaseSealed`)
2. Create `UseCase` or `AsyncUseCase` with handler ports
3. Use `CommandPort[Command]` and `QueryPort[Query]` for database access
4. Use `Port` subclasses for non-database dependencies

```python
from aod.application import UseCase, Command, Query, CommandPort, QueryPort

class PlaceOrder(Command[Order, None]):
    customer_id: str
    items: list[dict] = []

class GetOrder(Query[Order, Order | None]):
    order_id: str

class OrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]
    get_order: QueryPort[GetOrder]
    logger: Port
    email: EmailSender
```

## Adding New Handlers

1. Create `CommandHandler[C]` or `QueryHandler[Q]`
2. Declare `session` field for database access
3. Implement `handle()` method
4. Register in `Infrastructure(handlers=[...])`

```python
from aod.infrastructure import CommandHandler, QueryHandler

class PlaceOrderHandler(CommandHandler[PlaceOrder]):
    session: PostgresSession | None = None

    def handle(self, command: PlaceOrder) -> None: ...

class GetOrderHandler(QueryHandler[GetOrder]):
    session: PostgresSession | None = None

    def handle(self, query: GetOrder) -> Order | None:
        return None
```

## Adding New Projections

1. Create `ReadProjection`, `WriteProjection`, or `Projection`
2. Do NOT redeclare `session` field (inherited from base)
3. Implement `read()` or `write()` methods
4. Register in `Infrastructure(projections=[...])`

```python
from aod.infrastructure import ReadProjection, WriteProjection

class OrderSummaryProjection(ReadProjection):
    def read(self, model: object) -> list[dict]:
        return []

class ArchiveOrdersProjection(WriteProjection):
    def write(self, model: object) -> None: ...
```

## Generating Documentation with AutoDoc

1. Build domain types, use cases, handlers, projections
2. Create `BoundedContext`, `Infrastructure`, `Module`, `App`
3. Use `AutoDoc` to generate zensical site

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

## Running Tests

```bash
# Run all tests (excluding integration)
uv run pytest code/tests/ -q

# Run specific test file
uv run pytest code/tests/schema/test_render.py -v

# Run integration tests (writes files to disk)
RUN_INTEGRATION=1 uv run pytest code/tests/integration_tests/ -v

# Run tests with coverage
uv run pytest code/tests/ --cov=aod._internal.schema --cov-report=term-missing
```

## Schema System

The schema system provides introspection and documentation generation:

### Key Classes

- `App` — aggregates modules, validates no duplicate types
- `BoundedContext` — discovers entities, value objects, services
- `Infrastructure` — validates handler-port wiring
- `Module` — validates contracts have handlers, ports have implementations
- `AutoDoc` — generates zensical documentation sites

### Consistency Checks

All schema classes enforce consistency at construction time:

```python
from aod._internal.schema import App, BoundedContext, Infrastructure, Module

# App rejects duplicate entities across modules
# BoundedContext rejects non-RootEntity as aggregate roots
# Module rejects missing handlers for contracts
# Module rejects missing implementations for ports
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `DuplicateDomainTypeError` | Same class in multiple modules | Use distinct classes or combine modules |
| `MissingHandlerError` | Contract without handler | Add handler to Infrastructure |
| `MissingPortError` | Port without implementation | Add implementation to Infrastructure ports |
| `InvalidRootEntityTypeError` | Non-RootEntity as aggregate root | Use RootEntity subclass |
| `InvalidServiceTypeError` | Non-Service as service | Use Service subclass |

## Common Pitfalls

### Duplicate Domain Types

`App._validate` raises `DuplicateDomainTypeError` if the same class appears in multiple modules. Use distinct classes or combine into one module.

### Missing Handler Error

`Module._validate` requires a handler for every contract in the BoundedContext. Add handlers or remove use cases.

### Missing Port Error

`Module._validate` requires implementations for all ports. Add concrete port implementations to `Infrastructure(ports=[...])`.

### Projection Session Redeclaration

Do NOT redeclare `session` in projection subclasses. The base class provides it and validation will fail.

### Docstring Inheritance

Use `cls.__doc__` instead of `inspect.getdoc(cls)` to avoid inheriting docstrings from parent classes (e.g., `Generic`).

### Zensical Navigation

Use `mod.domain.name` (BoundedContext name) for nav labels, not `mod.name` (module name) for better readability.

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

## When Modifying This Code

- If you change `AutoDoc` rendering, update `render/auto_doc.py` and verify `test_render.py`
- If you change doc generation, update `docs/*.py` and verify `test_docs.py`
- If you change schema classes, update the relevant file and verify `test_schema.py`
- Always run `uv run ty check` and `uv run ruff check` before committing
- Always run `uv run pytest code/tests/ -q` to verify no regressions