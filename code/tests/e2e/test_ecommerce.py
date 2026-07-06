from __future__ import annotations

import pytest
from aod._internal.application.contracts import Command, Query
from aod._internal.application.event_bus import EventBus
from aod._internal.application.event_bus.null_event_bus import NullEventBus
from aod._internal.application.logger import Logger
from aod._internal.application.logger.null_logger import NullLogger
from aod._internal.application.port import Port
from aod._internal.application.use_case import UseCase
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.core.event_emitter import Event
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.domain.app import App
from aod._internal.domain.bounded_context import BoundedContext
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.service import Service
from aod._internal.domain.value_object import ValueObject
from aod._internal.infrastructure.container import AdapterContainer
from aod._internal.infrastructure.session import Session
from aod._internal.testing.doubles.application import SpyEventBus, SpyLogger, SpyUnitOfWork
from aod._internal.testing.faker import FakeDomain
from aod._internal.testing.helpers import assert_event_emitted, build, events_of

# ---------------------------------------------------------------------------
# Domain Layer — E-commerce domain
# ---------------------------------------------------------------------------


class Money(ValueObject):
    amount: int
    currency: str = "USD"


class OrderLine(ValueObject):
    product_id: str
    quantity: int
    unit_price: Money


class Address(ValueObject):
    street: str
    city: str
    zip_code: str


class OrderPlaced(Event):
    order_id: str
    customer_id: str
    total: int


class OrderShipped(Event):
    order_id: str


class OrderCancelled(Event):
    order_id: str
    reason: str


class Customer(RootEntity):
    id: str = Field(id=True)
    name: str
    email: str
    shipping_address: Address

    def update_email(self, new_email: str) -> None:
        self.email = new_email


class Product(Entity):
    id: str = Field(id=True)
    sku: str
    name: str
    price: Money


class Order(RootEntity):
    id: str = Field(id=True)
    customer_id: str
    lines: list[OrderLine]
    shipped: bool = False
    cancelled: bool = False

    def place(self) -> None:
        if self.shipped:
            raise ValueError("Order already shipped")
        if self.cancelled:
            raise ValueError("Order already cancelled")
        total = sum(line.unit_price.amount * line.quantity for line in self.lines)
        self._event_emitter.emit(
            OrderPlaced(
                order_id=self.id,
                customer_id=self.customer_id,
                total=total,
            )
        )

    def ship(self) -> None:
        if self.shipped:
            raise ValueError("Order already shipped")
        if self.cancelled:
            raise ValueError("Order already cancelled")
        self.shipped = True
        self._event_emitter.emit(OrderShipped(order_id=self.id))

    def cancel(self, reason: str) -> None:
        if self.shipped:
            raise ValueError("Cannot cancel shipped order")
        self.cancelled = True
        self._event_emitter.emit(OrderCancelled(order_id=self.id, reason=reason))


class InventoryService(Service):
    def check_availability(self, product_id: str, quantity: int) -> bool:
        return True

    def reserve(self, product_id: str, quantity: int) -> None:
        self._event_emitter.emit(Event())


# ---------------------------------------------------------------------------
# Application Layer — Ports & Use Cases
# ---------------------------------------------------------------------------


class EmailSender(Port):
    def send(self, to: str, subject: str, body: str) -> None: ...


class InventoryClient(Port):
    def reserve(self, product_id: str, quantity: int) -> bool:
        return True


class PlaceOrder(Command[Order, None]):
    order_id: str
    customer_id: str
    lines: list[OrderLine]


class GetOrder(Query[Order, Order | None]):
    order_id: str


class PlaceOrderUseCase(UseCase):
    email_sender: EmailSender
    inventory: InventoryClient
    logger: Logger
    event_bus: EventBus

    def run(self) -> None:
        cmd = PlaceOrder(
            order_id="ORD-001",
            customer_id="CUST-001",
            lines=[
                OrderLine(
                    product_id="PROD-001",
                    quantity=2,
                    unit_price=Money(amount=1000),
                ),
            ],
        )
        for line in cmd.lines:
            if not self.inventory.reserve(line.product_id, line.quantity):
                raise ValueError(f"Insufficient inventory for {line.product_id}")
        order = Order(
            id=cmd.order_id,
            customer_id=cmd.customer_id,
            lines=cmd.lines,
        )
        order.place()
        self.email_sender.send(
            to=f"{cmd.customer_id}@example.com",
            subject="Order Confirmed",
            body=f"Order {cmd.order_id} placed successfully",
        )


# ---------------------------------------------------------------------------
# Infrastructure Layer — Adapters
# ---------------------------------------------------------------------------


class FakeEmailSender(EmailSender):
    _sent: list[tuple[str, str, str]] = PrivateField(default_factory=list)

    @property
    def sent(self) -> list[tuple[str, str, str]]:
        return list(self._sent)

    def send(self, to: str, subject: str, body: str) -> None:
        self._sent.append((to, subject, body))


class FakeInventoryClient(InventoryClient):
    _reserved: list[tuple[str, int]] = PrivateField(default_factory=list)

    @property
    def reserved(self) -> list[tuple[str, int]]:
        return list(self._reserved)

    def reserve(self, product_id: str, quantity: int) -> bool:
        self._reserved.append((product_id, quantity))
        return True


class _SyncSession(Session):
    def execute(self, operation: object) -> object: ...
    def query(self, operation: object) -> object: ...
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def is_dirty(self) -> bool:
        return False


class EcommerceContainer(AdapterContainer):
    email_sender: FakeEmailSender
    inventory: FakeInventoryClient
    logger: Logger
    event_bus: EventBus


# ===========================================================================
# TESTS
# ===========================================================================


class TestValueObjects:
    def test_money_creation(self) -> None:
        m = Money(amount=1000, currency="EUR")
        assert m.amount == 1000
        assert m.currency == "EUR"

    def test_money_immutability(self) -> None:
        m = Money(amount=100)

        with pytest.raises(MutationForbiddenException):
            m.amount = 200

    def test_order_line_creation(self) -> None:
        line = OrderLine(
            product_id="PROD-001",
            quantity=2,
            unit_price=Money(amount=500),
        )
        assert line.product_id == "PROD-001"
        assert line.quantity == 2

    def test_address_value_object(self) -> None:
        addr = Address(street="123 Main St", city="Springfield", zip_code="12345")
        assert addr.city == "Springfield"


class TestEntities:
    def test_customer_creation(self) -> None:
        customer = Customer(
            id="CUST-001",
            name="Alice",
            email="alice@example.com",
            shipping_address=Address(street="123 Main St", city="Springfield", zip_code="12345"),
        )
        assert customer.name == "Alice"
        assert customer.email == "alice@example.com"

    def test_customer_update_email(self) -> None:
        customer = Customer(
            id="CUST-001",
            name="Alice",
            email="alice@example.com",
            shipping_address=Address(street="123 Main St", city="Springfield", zip_code="12345"),
        )
        customer.update_email("alice@new.com")
        assert customer.email == "alice@new.com"

    def test_order_creation(self) -> None:
        order = Order(
            id="ORD-001",
            customer_id="CUST-001",
            lines=[
                OrderLine(product_id="PROD-001", quantity=2, unit_price=Money(amount=1000)),
            ],
        )
        assert not order.shipped
        assert not order.cancelled

    def test_order_place_emits_event(self) -> None:
        order = Order(
            id="ORD-001",
            customer_id="CUST-001",
            lines=[
                OrderLine(product_id="PROD-001", quantity=2, unit_price=Money(amount=1000)),
            ],
        )
        order.place()
        events = events_of(order)
        assert_event_emitted(events, OrderPlaced, order_id="ORD-001", total=2000)

    def test_order_ship_emits_event(self) -> None:
        order = Order(id="ORD-001", customer_id="CUST-001", lines=[])
        order.place()
        order.ship()
        events = events_of(order)
        assert_event_emitted(events, OrderShipped, order_id="ORD-001")

    def test_order_cancel_emits_event(self) -> None:
        order = Order(id="ORD-001", customer_id="CUST-001", lines=[])
        order.place()
        order.cancel("changed mind")
        events = events_of(order)
        assert_event_emitted(events, OrderCancelled, order_id="ORD-001", reason="changed mind")

    def test_cannot_ship_cancelled_order(self) -> None:
        order = Order(id="ORD-001", customer_id="CUST-001", lines=[])
        order.place()
        order.cancel("no longer needed")
        with pytest.raises(ValueError, match="already cancelled"):
            order.ship()

    def test_cannot_cancel_shipped_order(self) -> None:
        order = Order(id="ORD-001", customer_id="CUST-001", lines=[])
        order.place()
        order.ship()
        with pytest.raises(ValueError, match="Cannot cancel shipped order"):
            order.cancel("oops")

    def test_cannot_place_twice(self) -> None:
        order = Order(id="ORD-001", customer_id="CUST-001", lines=[])
        order.place()
        order.place()

    def test_product_entity(self) -> None:
        product = Product(id="PROD-001", sku="PROD-001", name="Widget", price=Money(amount=999))
        assert product.sku == "PROD-001"
        assert product.name == "Widget"


class TestDomainService:
    def test_inventory_service(self) -> None:
        service = InventoryService()
        assert service.check_availability("PROD-001", 5) is True
        service.reserve("PROD-001", 5)


class TestBoundedContext:
    def test_bounded_context_with_roots_and_services(self) -> None:
        ctx = BoundedContext(
            aggregate_roots=[Customer, Order],
            services=[InventoryService],
            name="ecommerce",
        )
        assert ctx.name == "ecommerce"
        assert Customer in ctx.aggregate_roots
        assert Order in ctx.aggregate_roots
        assert InventoryService in ctx.services
        assert Money in ctx.value_objects
        assert OrderLine in ctx.value_objects
        assert Address in ctx.value_objects

    def test_bounded_context_describe(self) -> None:
        ctx = BoundedContext(
            aggregate_roots=[Customer, Order],
            name="ecommerce",
        )
        docs = ctx.describe()
        assert len(docs) >= 2

    def test_app_with_contexts(self) -> None:
        ctx = BoundedContext(
            aggregate_roots=[Customer, Order],
            services=[InventoryService],
            name="ecommerce",
        )
        app = App("MyShop", ctx)
        assert app.name == "MyShop"
        assert len(app.contexts) == 1

    def test_app_describe(self) -> None:
        ctx = BoundedContext(
            aggregate_roots=[Customer, Order],
            name="ecommerce",
        )
        app = App("MyShop", ctx)
        desc = app.describe()
        assert "ecommerce" in desc


class TestCommandsAndQueries:
    def test_place_order_command(self) -> None:
        cmd = PlaceOrder(
            order_id="ORD-001",
            customer_id="CUST-001",
            lines=[
                OrderLine(product_id="PROD-001", quantity=2, unit_price=Money(amount=1000)),
            ],
        )
        assert cmd.order_id == "ORD-001"
        assert len(cmd.lines) == 1

    def test_get_order_query(self) -> None:
        q = GetOrder(order_id="ORD-001")
        assert q.order_id == "ORD-001"


class TestUseCase:
    def test_use_case_with_real_adapters(self) -> None:
        email_sender = FakeEmailSender()
        inventory = FakeInventoryClient()
        uc = PlaceOrderUseCase(
            email_sender=email_sender,
            inventory=inventory,
            logger=NullLogger(),
            event_bus=NullEventBus(),
        )
        uc.run()
        assert len(inventory.reserved) == 1
        assert len(email_sender.sent) == 1
        assert "Confirmed" in email_sender.sent[0][1]

    def test_use_case_collects_events(self) -> None:
        email_sender = FakeEmailSender()
        inventory = FakeInventoryClient()
        uc = PlaceOrderUseCase(
            email_sender=email_sender,
            inventory=inventory,
            logger=NullLogger(),
            event_bus=NullEventBus(),
        )
        uc.run()
        assert len(uc.events) >= 1

    def test_use_case_with_uow_logger_event_bus(self) -> None:
        email_sender = FakeEmailSender()
        inventory = FakeInventoryClient()
        uow = SpyUnitOfWork()
        logger = SpyLogger()
        bus = SpyEventBus()
        uc = PlaceOrderUseCase(
            email_sender=email_sender,
            inventory=inventory,
            uow=uow,
            logger=logger,
            event_bus=bus,
        )
        uc.run()
        assert uow.committed
        assert not uow.rolled_back
        completions = [e for e in logger.entries if "completed" in str(e.msg)]
        assert len(completions) == 1
        assert len(bus.published) >= 1

    def test_use_case_events_immutable_from_outside(self) -> None:
        uc = PlaceOrderUseCase(
            email_sender=FakeEmailSender(),
            inventory=FakeInventoryClient(),
            logger=NullLogger(),
            event_bus=NullEventBus(),
        )
        uc.run()
        assert len(uc.events) >= 1

        with pytest.raises(MutationForbiddenException):
            uc.events = []


class TestContainerAndInjection:
    def test_container_with_adapters(self) -> None:
        email_sender = FakeEmailSender()
        inventory = FakeInventoryClient()
        container = EcommerceContainer(
            email_sender=email_sender,
            inventory=inventory,
            logger=NullLogger(),
            event_bus=NullEventBus(),
        )
        assert isinstance(container.email_sender, FakeEmailSender)
        assert isinstance(container.inventory, FakeInventoryClient)

    def test_inject_adapters_into_use_case(self) -> None:
        email_sender = FakeEmailSender()
        inventory = FakeInventoryClient()
        container = EcommerceContainer(
            email_sender=email_sender,
            inventory=inventory,
            logger=NullLogger(),
            event_bus=NullEventBus(),
        )
        uc = container.adapt(PlaceOrderUseCase)
        assert isinstance(uc.email_sender, FakeEmailSender)
        assert isinstance(uc.inventory, FakeInventoryClient)

    def test_inject_with_session(self) -> None:
        email_sender = FakeEmailSender()
        inventory = FakeInventoryClient()
        container = EcommerceContainer(
            email_sender=email_sender,
            inventory=inventory,
            sessions={_SyncSession},
            logger=NullLogger(),
            event_bus=NullEventBus(),
        )
        uc = container.adapt(PlaceOrderUseCase)
        uc.run()
        assert len(uc.events) >= 1

    def test_full_integration_via_container(self) -> None:
        email_sender = FakeEmailSender()
        inventory = FakeInventoryClient()
        logger = SpyLogger()
        bus = SpyEventBus()
        container = EcommerceContainer(
            email_sender=email_sender,
            inventory=inventory,
            sessions={_SyncSession},
            logger=logger,
            event_bus=bus,
        )
        uc = container.adapt(PlaceOrderUseCase)
        uc.run()
        assert len(inventory.reserved) == 1
        assert len(email_sender.sent) == 1
        assert len(uc.events) >= 1
        assert len(bus.published) >= 1
        completions = [e for e in logger.entries if "completed" in str(e.msg)]
        assert len(completions) == 1


class TestFakeDomain:
    def test_fake_customer(self) -> None:
        fake = FakeDomain(Customer)
        customer = fake(name="Bob")
        assert customer.name == "Bob"
        assert isinstance(customer.id, str)
        assert isinstance(customer.shipping_address, Address)

    def test_fake_order(self) -> None:
        fake = FakeDomain(
            Order,
            id="ORD-001",
            customer_id="CUST-001",
            lines=[],
            shipped=False,
            cancelled=False,
        )
        order = fake()
        assert isinstance(order.id, str)
        assert isinstance(order.lines, list)

    def test_fake_order_with_overrides(self) -> None:
        fake = FakeDomain(
            Order,
            id="ORD-001",
            customer_id="CUST-001",
            lines=[],
            shipped=False,
            cancelled=False,
        )
        order = fake(id="ORD-CUSTOM")
        assert order.id == "ORD-CUSTOM"
        assert order.customer_id == "CUST-001"

    def test_fake_batch(self) -> None:
        fake = FakeDomain(Customer)
        customers = fake.batch(3)
        assert len(customers) == 3
        assert all(isinstance(c, Customer) for c in customers)


class TestBuildHelper:
    def test_build_skips_validation(self) -> None:
        order = build(
            Order,
            id="ORD-001",
            customer_id="CUST-001",
            lines=[],
            shipped=False,
            cancelled=False,
        )
        assert order.id == "ORD-001"

    def test_build_with_nested_value_objects(self) -> None:
        order = build(
            Order,
            id="ORD-001",
            customer_id="CUST-001",
            lines=[
                OrderLine(product_id="PROD-001", quantity=1, unit_price=Money(amount=500)),
            ],
            shipped=False,
            cancelled=False,
        )
        assert len(order.lines) == 1
