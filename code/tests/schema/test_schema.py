"""Tests for schema classes: BoundedContext, Infrastructure, Module, App."""

from __future__ import annotations

import pytest
from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler import CommandPort, QueryPort
from aod._internal.application.port import Port
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.core.domain_exception import (
    DuplicateDomainTypeError,
    InvalidEntityTypeError,
    InvalidRootEntityTypeError,
    InvalidServiceTypeError,
    MissingHandlerError,
)
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.service import Service
from aod._internal.infrastructure.handlers import CommandHandler, QueryHandler
from aod._internal.infrastructure.projection import ReadProjection
from aod._internal.infrastructure.session import Session
from aod._internal.schema.app import App
from aod._internal.schema.bounded_context import BoundedContext
from aod._internal.schema.infrastructure import Infrastructure
from aod._internal.schema.module import Module
from aod.domain import Field

# ---- Domain types ----


class LineItem(Entity):
    id: int = Field(id=True)
    sku: str


class Order(RootEntity):
    id: str = Field(id=True)
    total: float = 0.0
    lines: list[LineItem] = []


class Invoice(RootEntity):
    id: int = Field(id=True)
    amount: float


class PricingService(Service):
    def calculate_discount(self, total: float) -> float:
        return total * 0.1


# ---- Contracts ----


class PlaceOrder(Command[Order, None]):
    order_id: str


class GetOrder(Query[Order, Order | None]):
    order_id: str


class IssueInvoice(Command[Invoice, None]):
    invoice_id: str


# ---- Handlers ----


class MySession(Session):
    _connection: object = None

    def execute(self, operation: object) -> object:
        return None

    def query(self, operation: object) -> object:
        return None

    def begin(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return False


class PlaceOrderHandler(CommandHandler[PlaceOrder]):
    session: MySession

    def handle(self, command: PlaceOrder) -> None:
        pass


class GetOrderHandler(QueryHandler[GetOrder]):
    session: MySession

    def handle(self, query: GetOrder) -> Order | None:
        return None


class IssueInvoiceHandler(CommandHandler[IssueInvoice]):
    session: MySession

    def handle(self, command: IssueInvoice) -> None:
        pass


# ---- Custom Port ----


class EmailSender(Port):
    def send(self, to: str, subject: str) -> None:
        pass


# ---- Port implementations ----


class ConsoleLogger(Port):
    def info(self, msg: str) -> None:
        pass


class SmtpSender(EmailSender):
    def send(self, to: str, subject: str) -> None:
        pass


class FakeLogger(Port):
    pass


class FakeEventBus(Port):
    pass


class FakeCache(Port):
    pass


# ---- Use Cases ----


class OrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]
    get_order: QueryPort[GetOrder]
    logger: Port
    email: EmailSender

    def run(self, order_id: str) -> None:
        pass


# ============================================================
# BoundedContext
# ============================================================


class TestBoundedContext:
    def test_construct_with_all_params(self) -> None:
        bc = BoundedContext(
            aggregate_roots=[Order],
            services=[PricingService],
            use_cases=[OrderUseCase],
            name="orders",
        )
        assert bc.name == "orders"
        assert bc.aggregate_roots == (Order,)
        assert bc.services == (PricingService,)
        assert bc.use_cases == (OrderUseCase,)
        assert PlaceOrder in bc.contracts
        assert GetOrder in bc.contracts

    def test_construct_defaults(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order])
        assert bc.name is None
        assert bc.services == ()
        assert bc.use_cases == ()

    def test_construct_no_params(self) -> None:
        bc = BoundedContext()
        assert bc.aggregate_roots == ()
        assert bc.services == ()
        assert bc.use_cases == ()

    def test_contracts_by_root(self) -> None:
        bc = BoundedContext(
            aggregate_roots=[Order],
            use_cases=[OrderUseCase],
        )
        assert Order in bc.contracts_by_root
        assert PlaceOrder in bc.contracts_by_root[Order]
        assert GetOrder in bc.contracts_by_root[Order]

    def test_raises_on_non_entity_as_root(self) -> None:
        with pytest.raises(InvalidEntityTypeError):
            BoundedContext(aggregate_roots=[PricingService])  # ty: ignore[invalid-argument-type]

    def test_raises_on_entity_as_root(self) -> None:
        with pytest.raises(InvalidRootEntityTypeError):
            BoundedContext(aggregate_roots=[LineItem])  # ty: ignore[invalid-argument-type]

    def test_raises_on_non_service(self) -> None:
        with pytest.raises(InvalidServiceTypeError):
            BoundedContext(services=[Order])  # ty: ignore[invalid-argument-type]

    def test_repr_with_name(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order], name="orders")
        assert repr(bc) == "orders"

    def test_repr_without_name(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order])
        assert "BoundedContext" in repr(bc)

    def test_ports_extracted_from_use_cases(self) -> None:
        bc = BoundedContext(use_cases=[OrderUseCase])
        assert EmailSender in bc.ports

    def test_value_objects_discovered(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order])
        assert len(bc.value_objects) == 0

    def test_entities_discovered(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order])
        ent_names = {e.__name__ for e in bc.entities}
        assert "LineItem" in ent_names

    def test_multiple_roots(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order, Invoice])
        assert len(bc.aggregate_roots) == 2

    def test_accepts_async_use_case(self) -> None:
        class MyAsyncUseCase(AsyncUseCase):
            async def run(self, x: int) -> None:
                pass

        bc = BoundedContext(use_cases=[MyAsyncUseCase])
        assert MyAsyncUseCase in bc.use_cases


# ============================================================
# Infrastructure
# ============================================================


class TestInfrastructure:
    def test_construct_empty(self) -> None:
        infra = Infrastructure()
        assert infra.handlers == ()
        assert infra.sessions == ()
        assert infra.projections == ()

    def test_construct_with_handlers(self) -> None:
        infra = Infrastructure(
            handlers=[PlaceOrderHandler],
        )
        assert len(infra.handlers) == 1
        assert len(infra.sessions) == 1  # extracted from handlers
        assert MySession in infra.sessions

    def test_construct_with_projections(self) -> None:
        class TestProj(ReadProjection):
            def read(self, model: object) -> list[Order]:
                return []

        infra = Infrastructure(projections=[TestProj])
        assert len(infra.projections) == 1

    def test_duplicate_contract_raises(self) -> None:
        with pytest.raises(DuplicateDomainTypeError):
            Infrastructure(handlers=[PlaceOrderHandler, PlaceOrderHandler])


# ============================================================
# Module
# ============================================================


class TestModule:
    def test_construct_valid(self) -> None:
        bc = BoundedContext(
            aggregate_roots=[Order],
            use_cases=[OrderUseCase],
        )
        infra = Infrastructure(
            handlers=[PlaceOrderHandler, GetOrderHandler],
            ports=[ConsoleLogger, SmtpSender],
        )
        mod = Module(name="orders", context=bc, infrastructure=infra)
        assert mod.name == "orders"
        assert mod.context is bc
        assert mod.infrastructure is infra

    def test_missing_handler_raises(self) -> None:
        bc = BoundedContext(
            aggregate_roots=[Order],
            use_cases=[OrderUseCase],
        )
        infra = Infrastructure(handlers=[])
        with pytest.raises(MissingHandlerError):
            Module(name="orders", context=bc, infrastructure=infra)

    def test_no_context_contracts_ok(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order])
        infra = Infrastructure(handlers=[])
        mod = Module(name="empty", context=bc, infrastructure=infra)
        assert mod.name == "empty"


# ============================================================
# App
# ============================================================


class TestApp:
    def test_construct_valid(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order], name="orders")
        infra = Infrastructure(handlers=[PlaceOrderHandler])
        mod = Module(name="orders", context=bc, infrastructure=infra)
        app = App(name="ecommerce", modules=[mod])
        assert app.name == "ecommerce"
        assert len(app.modules) == 1

    def test_duplicate_entity_raises(self) -> None:
        bc1 = BoundedContext(aggregate_roots=[Order], name="orders")
        bc2 = BoundedContext(aggregate_roots=[Order], name="sales")
        infra = Infrastructure(handlers=[PlaceOrderHandler])
        mod1 = Module(name="orders", context=bc1, infrastructure=infra)
        mod2 = Module(name="sales", context=bc2, infrastructure=infra)
        with pytest.raises(DuplicateDomainTypeError):
            App(name="ecommerce", modules=[mod1, mod2])

    def test_duplicate_service_raises(self) -> None:
        bc1 = BoundedContext(services=[PricingService])
        bc2 = BoundedContext(services=[PricingService])
        infra = Infrastructure()
        mod1 = Module(name="a", context=bc1, infrastructure=infra)
        mod2 = Module(name="b", context=bc2, infrastructure=infra)
        with pytest.raises(DuplicateDomainTypeError):
            App(name="x", modules=[mod1, mod2])

    def test_duplicate_use_case_raises(self) -> None:
        bc1 = BoundedContext(use_cases=[OrderUseCase])
        bc2 = BoundedContext(use_cases=[OrderUseCase])
        infra = Infrastructure(
            handlers=[PlaceOrderHandler, GetOrderHandler],
            ports=[ConsoleLogger, SmtpSender],
        )
        mod1 = Module(name="a", context=bc1, infrastructure=infra)
        mod2 = Module(name="b", context=bc2, infrastructure=infra)
        with pytest.raises(DuplicateDomainTypeError):
            App(name="x", modules=[mod1, mod2])

    def test_duplicate_handler_raises(self) -> None:
        bc = BoundedContext(name="shared")
        infra1 = Infrastructure(handlers=[PlaceOrderHandler])
        infra2 = Infrastructure(handlers=[PlaceOrderHandler])
        mod1 = Module(name="a", context=bc, infrastructure=infra1)
        mod2 = Module(name="b", context=bc, infrastructure=infra2)
        with pytest.raises(DuplicateDomainTypeError):
            App(name="x", modules=[mod1, mod2])

    def test_duplicate_contract_raises(self) -> None:
        bc1 = BoundedContext(use_cases=[OrderUseCase])
        bc2 = BoundedContext(use_cases=[OrderUseCase])
        infra = Infrastructure(
            handlers=[PlaceOrderHandler, GetOrderHandler],
            ports=[ConsoleLogger, SmtpSender],
        )
        mod1 = Module(name="a", context=bc1, infrastructure=infra)
        mod2 = Module(name="b", context=bc2, infrastructure=infra)
        with pytest.raises(DuplicateDomainTypeError):
            App(name="x", modules=[mod1, mod2])

    def test_no_duplicate_clean_run(self) -> None:
        bc1 = BoundedContext(aggregate_roots=[Order], name="orders", use_cases=[OrderUseCase])
        bc2 = BoundedContext(aggregate_roots=[Invoice], name="invoices")
        infra1 = Infrastructure(
            handlers=[PlaceOrderHandler, GetOrderHandler],
            ports=[ConsoleLogger, SmtpSender],
        )
        infra2 = Infrastructure()
        mod1 = Module(name="orders", context=bc1, infrastructure=infra1)
        mod2 = Module(name="invoices", context=bc2, infrastructure=infra2)
        app = App(name="multi", modules=[mod1, mod2])
        assert len(app.modules) == 2


# ============================================================
# MissingHandlerError
# ============================================================


class TestMissingHandlerError:
    def test_message(self) -> None:
        err = MissingHandlerError("test message")
        assert str(err) == "test message"
