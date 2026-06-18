#!/usr/bin/env python3
"""Generates a complete zensical documentation site from a sample app.

Run:  uv run python code/tests/schema/make_example_site.py
Then: cd example-site && uv run zensical build --clean
"""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path

from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler import (
    AsyncCommandPort,
    AsyncQueryPort,
    CommandPort,
    QueryPort,
)
from aod._internal.application.port import Port
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.application.unit_of_work import UnitOfWork
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.service import Service
from aod._internal.domain.value_object import ValueObject
from aod._internal.infrastructure.handlers import (
    AsyncCommandHandler,
    AsyncQueryHandler,
    CommandHandler,
    QueryHandler,
)
from aod._internal.infrastructure.projection import (
    AsyncWriteProjection,
    ReadProjection,
    WriteProjection,
)
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.schema.app import App
from aod._internal.schema.bounded_context import BoundedContext
from aod._internal.schema.infrastructure import Infrastructure
from aod._internal.schema.module import Module
from aod._internal.schema.render import AutoDoc

# ---- Value Objects ----


class OrderId(ValueObject):
    """Unique identifier for an order in the system."""

    value: str


class CustomerId(ValueObject):
    """Unique identifier for a customer."""

    value: str


class Address(ValueObject):
    """Postal address for shipping and billing."""

    street: str
    city: str
    zip_code: str


class OrderLine(ValueObject):
    """A single product line within an order."""

    product_id: str
    quantity: int
    price: float


# ---- Entities ----


class Customer(Entity):
    """A customer in the e-commerce platform."""

    id: CustomerId
    name: str
    address: Address


# ---- Root Entities ----


class Order(RootEntity):
    """Root aggregate for the ordering subdomain."""

    id: OrderId
    customer_id: CustomerId
    lines: list[OrderLine] = []
    total: float = 0.0
    total: float = 0.0

    def add_line(self, product_id: str, quantity: int, price: float) -> None: ...
    def calculate_total(self) -> float:
        return 0.0


class Invoice(RootEntity):
    """Root aggregate for the invoicing subdomain."""

    id: str
    order_id: OrderId
    amount: float = 0.0
    paid: bool = False
    paid: bool = False

    def mark_paid(self) -> None: ...


# ---- Services ----


class PricingService(Service):
    """Applies discount codes and calculates final prices."""

    def apply_discount(self, base: float, code: str) -> float:
        return base * 0.9


class TaxService(Service):
    """Calculates tax amounts based on region and price."""

    def calculate_tax(self, amount: float, region: str) -> float:
        return amount * 0.21


# ---- Contracts ----


class PlaceOrder(Command[Order, None]):
    customer_id: str
    items: list[dict] = []


class GetOrder(Query[Order, Order | None]):
    order_id: str


class CancelOrder(Command[Order, None]):
    order_id: str


class ListOrders(Query[Order, list[Order]]):
    customer_id: str


class CreateInvoice(Command[Invoice, None]):
    order_id: str


class GetInvoice(Query[Invoice, Invoice | None]):
    invoice_id: str


# ---- Ports ----


class EmailSender(Port):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None: ...


class PaymentGateway(Port):
    @abstractmethod
    def charge(self, amount: float, token: str) -> bool: ...


class InventoryClient(Port):
    @abstractmethod
    def reserve(self, product_id: str, quantity: int) -> bool: ...


class AuditLogger(Port):
    @abstractmethod
    def log(self, action: str, details: dict) -> None: ...


# ---- Port implementations ----


class SmtpSender(EmailSender):
    def send(self, to: str, subject: str, body: str) -> None: ...


class StripeGateway(PaymentGateway):
    def charge(self, amount: float, token: str) -> bool:
        return True


class FakeInventory(InventoryClient):
    def reserve(self, product_id: str, quantity: int) -> bool:
        return True


class ConsoleAuditLogger(AuditLogger):
    def log(self, action: str, details: dict) -> None: ...


class FakeUnitOfWork(UnitOfWork):
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


# ---- Sessions ----


class PostgresSession(Session):
    _connection: object | None = None


class RedisSession(Session):
    _connection: object | None = None


# ---- Use Cases ----


class OrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]
    get_order: QueryPort[GetOrder]
    cancel_order: CommandPort[CancelOrder]
    list_orders: QueryPort[ListOrders]
    logger: Port
    email: EmailSender
    payment: PaymentGateway
    inventory: InventoryClient


class InvoiceUseCase(UseCase):
    create_invoice: CommandPort[CreateInvoice]
    get_invoice: QueryPort[GetInvoice]
    logger: Port
    audit: AuditLogger


class AsyncOrderUseCase(AsyncUseCase):
    place_order: AsyncCommandPort[PlaceOrder]
    get_order: AsyncQueryPort[GetOrder]
    logger: Port
    email: EmailSender


# ---- Handlers ----


class PlaceOrderHandler(CommandHandler[PlaceOrder]):
    session: PostgresSession | None = None

    def handle(self, command: PlaceOrder) -> None: ...


class GetOrderHandler(QueryHandler[GetOrder]):
    session: PostgresSession | None = None

    def handle(self, query: GetOrder) -> Order | None:
        return None


class CancelOrderHandler(CommandHandler[CancelOrder]):
    session: PostgresSession | None = None

    def handle(self, command: CancelOrder) -> None: ...


class ListOrdersHandler(QueryHandler[ListOrders]):
    session: RedisSession | None = None

    def handle(self, query: ListOrders) -> list[Order]:
        return []


class CreateInvoiceHandler(CommandHandler[CreateInvoice]):
    session: PostgresSession | None = None

    def handle(self, command: CreateInvoice) -> None: ...


class GetInvoiceHandler(QueryHandler[GetInvoice]):
    session: PostgresSession | None = None

    def handle(self, query: GetInvoice) -> Invoice | None:
        return None


class AsyncPlaceOrderHandler(AsyncCommandHandler[PlaceOrder]):
    session: AsyncSession | None = None

    async def handle(self, command: PlaceOrder) -> None: ...


class AsyncGetOrderHandler(AsyncQueryHandler[GetOrder]):
    session: AsyncSession | None = None

    async def handle(self, query: GetOrder) -> Order | None:
        return None


# ---- Projections ----


class OrderSummaryProjection(ReadProjection):
    def read(self, model: object) -> list[dict]:
        return []


class InvoiceReportProjection(ReadProjection):
    def read(self, model: object) -> list[dict]:
        return []


class ArchiveOrdersProjection(WriteProjection):
    def write(self, model: object) -> None: ...


class AsyncOrderSyncProjection(AsyncWriteProjection):
    async def write(self, model: object) -> None: ...


# ---- Build the site ----

OUTPUT = Path(__file__).parent / "example-site"


def main() -> None:
    bc_orders = BoundedContext(
        aggregate_roots=[Order],
        services=[PricingService, TaxService],
        use_cases=[OrderUseCase],
        name="Orders",
    )

    bc_invoicing = BoundedContext(
        aggregate_roots=[Invoice],
        use_cases=[InvoiceUseCase],
        name="Invoicing",
    )

    infra_orders = Infrastructure(
        handlers=[
            PlaceOrderHandler,
            GetOrderHandler,
            CancelOrderHandler,
            ListOrdersHandler,
        ],
        projections=[
            OrderSummaryProjection,
            ArchiveOrdersProjection,
        ],
        ports=[
            FakeUnitOfWork,
            SmtpSender,
            StripeGateway,
            FakeInventory,
        ],
    )

    infra_invoicing = Infrastructure(
        handlers=[
            CreateInvoiceHandler,
            GetInvoiceHandler,
        ],
        projections=[
            InvoiceReportProjection,
        ],
        ports=[
            FakeUnitOfWork,
            ConsoleAuditLogger,
        ],
    )

    mod_orders = Module(name="orders", context=bc_orders, infrastructure=infra_orders)
    mod_invoicing = Module(name="invoicing", context=bc_invoicing, infrastructure=infra_invoicing)

    app = App(
        name="E-Commerce Platform",
        modules=[mod_orders, mod_invoicing],
        description="A domain-driven e-commerce platform built with attack-on-domain.",
    )

    doc = AutoDoc(
        app,
        OUTPUT,
        site_name="E-Commerce Docs",
        site_description="DDD documentation for the E-Commerce Platform",
        repo_url="https://github.com/example/ecommerce",
        repo_name="ecommerce",
    )

    result = doc.generate()
    print(f"Site generated at: {result}")
    print(f"Run: cd {result} && uv run zensical build --clean")


if __name__ == "__main__":
    main()
