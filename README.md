# attack-on-domain

Domain-Driven Design building blocks for Python 3.14+: entities, value objects, aggregates, CQRS, ports and adapters, use cases, domain events, invariants, and dependency injection.

## Install

```bash
pip install attack-on-domain
```

Requires **Python 3.14+**.

## Quick Example

```python
from aod.domain import RootEntity, ValueObject, Event
from aod.application import UseCase, Command, CommandPort
from aod.infrastructure import CommandHandler, Session, AdapterContainer


class SqlSession(Session):
    def execute(self, operation: object) -> None: ...


class OrderId(ValueObject):
    value: str

class OrderPlaced(Event):
    order_id: str
    total: float

class Order(RootEntity):
    id: OrderId
    total: float

    def place(self) -> None:
        self._event_emitter.emit(OrderPlaced(order_id=self.id.value, total=self.total))

class PlaceOrder(Command[Order, None]):
    order_id: str
    total: float

class PlaceOrderHandler(CommandHandler[PlaceOrder]):
    session: SqlSession

    def handle(self, command: PlaceOrder) -> None:
        order = Order(id=OrderId(value=command.order_id), total=command.total)
        self.session.execute(order)

class PlaceOrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]

    def run(self, order_id: str, total: float) -> None:
        order = Order(id=OrderId(value=order_id), total=total)
        order.place()
        self.place_order.handle(PlaceOrder(order_id=order_id, total=total))

container = AdapterContainer(handlers=[PlaceOrderHandler])
use_case = container.adapt(PlaceOrderUseCase)
use_case.run(order_id="1", total=99.99)
```

## Key Features

- **Domain Building Blocks** — Entity, RootEntity, ValueObject, Aggregate with mutation guards and identity
- **Domain Events** — Immutable, auto-timestamped, automatically collected by use cases
- **CQRS** — Commands, Queries, and dedicated handlers for clean read/write separation
- **Use Cases** — Application-layer orchestration with auto-wired ports, logging, and transaction management
- **Business Invariants** — Type-safe field and model-level rules enforced at construction time
- **Testing** — Spy containers, session stubs, fakers, and event assertions
- **Hexagonal Architecture** — Ports, adapters, and dependency injection through containers

## Documentation

Full documentation at [alfonsocuesta.github.io/attack-on-domain](https://alfonsocuesta.github.io/attack-on-domain/)

- [Getting Started](docs/getting-started/installation.md) — Install, quickstart, and concepts
- [Domain Layer](docs/domain/index.md) — Entities, Value Objects, Services, Events, Invariants
- [Application Layer](docs/application/index.md) — Use Cases, Ports, Contracts
- [Infrastructure Layer](docs/infrastructure/index.md) — Sessions, Handlers, Containers, Injection
- [Testing](docs/testing/index.md) — Spies, stubs, fakers, and assertions
- [DDD to AoD](docs/getting-started/mapping.md) — Map DDD concepts to framework components
- [API Reference](docs/api/index.md) — Full class and method reference

## License

Apache 2.0