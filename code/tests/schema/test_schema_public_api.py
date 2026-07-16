"""Tests for public API imports from aod._internal.schema."""

from __future__ import annotations

import pytest
from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler import CommandPort, QueryPort
from aod._internal.application.port import Port
from aod._internal.application.use_case import UseCase
from aod._internal.core.domain_exception import (
    DuplicateDomainTypeError,
    InvalidRootEntityTypeError,
    InvalidServiceTypeError,
    MissingHandlerError,
)
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.service import Service
from aod._internal.infrastructure.handlers import CommandHandler, QueryHandler
from aod._internal.infrastructure.session import Session
from aod._internal.schema import App, AutoDoc, BoundedContext, Infrastructure, Module
from aod.domain import Field

# ---- Test domain types ----


class Order(RootEntity):
    id: str = Field(id=True)
    total: float = 0.0


class PlaceOrder(Command[Order, None]):
    order_id: str


class GetOrder(Query[Order, Order | None]):
    order_id: str


class EmailSender(Port):
    def send(self, to: str) -> None: ...


class SmtpSender(EmailSender):
    def send(self, to: str) -> None: ...


class OrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]
    get_order: QueryPort[GetOrder]
    logger: Port
    email: EmailSender


class _TestSession(Session):
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def is_dirty(self) -> bool:
        return False


class PlaceOrderHandler(CommandHandler[PlaceOrder]):
    session: _TestSession

    def handle(self, command: PlaceOrder) -> None: ...


class GetOrderHandler(QueryHandler[GetOrder]):
    session: _TestSession

    def handle(self, query: GetOrder) -> Order | None:
        return None


class PricingService(Service):
    def calculate_total(self, base: float) -> float:
        return base * 1.1


# ---- Tests ----


class TestPublicAPIImports:
    """Verify that key classes are importable from aod._internal.schema."""

    def test_app_importable(self) -> None:
        assert App is not None
        assert hasattr(App, "__init__")

    def test_bounded_context_importable(self) -> None:
        assert BoundedContext is not None
        assert hasattr(BoundedContext, "__init__")

    def test_infrastructure_importable(self) -> None:
        assert Infrastructure is not None
        assert hasattr(Infrastructure, "__init__")

    def test_module_importable(self) -> None:
        assert Module is not None
        assert hasattr(Module, "__init__")

    def test_auto_doc_importable(self) -> None:
        assert AutoDoc is not None
        assert hasattr(AutoDoc, "__init__")
        assert hasattr(AutoDoc, "generate")

    def test_all_exports(self) -> None:
        import aod._internal.schema as schema_mod

        assert "App" in schema_mod.__all__
        assert "BoundedContext" in schema_mod.__all__
        assert "Infrastructure" in schema_mod.__all__
        assert "Module" in schema_mod.__all__
        assert "AutoDoc" in schema_mod.__all__


class TestSchemaConsistencyChecks:
    """Verify that App, Infrastructure, Module, BoundedContext enforce consistency."""

    def test_app_rejects_duplicate_entities(self) -> None:
        bc1 = BoundedContext(aggregate_roots=[Order], name="A")
        bc2 = BoundedContext(aggregate_roots=[Order], name="B")
        infra = Infrastructure()
        mod1 = Module(name="a", context=bc1, infrastructure=infra)
        mod2 = Module(name="b", context=bc2, infrastructure=infra)

        with pytest.raises(DuplicateDomainTypeError):
            App(name="Dup", modules=[mod1, mod2])

    def test_module_rejects_missing_handler(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order], use_cases=[OrderUseCase])
        infra = Infrastructure()

        with pytest.raises(MissingHandlerError):
            Module(name="bad", context=bc, infrastructure=infra)

    def test_module_rejects_missing_port(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order], use_cases=[OrderUseCase])
        infra = Infrastructure(handlers=[PlaceOrderHandler, GetOrderHandler])

        with pytest.raises(Exception):
            Module(name="bad", context=bc, infrastructure=infra)

    def test_bounded_context_rejects_non_root_entity(self) -> None:
        class LineItem(Entity):
            id: int = Field(id=True)

        with pytest.raises(InvalidRootEntityTypeError):
            BoundedContext(aggregate_roots=[LineItem])  # ty: ignore[invalid-argument-type]

    def test_bounded_context_rejects_non_service(self) -> None:
        with pytest.raises(InvalidServiceTypeError):
            BoundedContext(services=[Order])  # ty: ignore[invalid-argument-type]
