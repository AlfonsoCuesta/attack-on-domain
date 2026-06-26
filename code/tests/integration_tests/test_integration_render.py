"""Integration test for AutoDoc — runs only with RUN_INTEGRATION=1.

Generates a real zensical site into a temp directory and verifies
the complete output structure and key content.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

import pytest
from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler import CommandPort, QueryPort
from aod._internal.application.port import Port
from aod._internal.application.unit_of_work import UnitOfWork
from aod._internal.application.use_case import UseCase
from aod._internal.domain.entity import RootEntity
from aod._internal.domain.entity_id import EntityId
from aod._internal.domain.value_object import ValueObject
from aod._internal.infrastructure.handlers import CommandHandler, QueryHandler
from aod._internal.infrastructure.session import Session
from aod._internal.schema.app import App
from aod._internal.schema.bounded_context import BoundedContext
from aod._internal.schema.infrastructure import Infrastructure
from aod._internal.schema.module import Module
from aod._internal.schema.render import AutoDoc
from aod.domain import Field

# ---- domain types ----


class OrderId(EntityId):
    value: str


class Order(RootEntity):
    id: OrderId = Field(id=True)
    total: float = 0.0


class LineItem(ValueObject):
    product: str
    quantity: int


# ---- contracts ----


class PlaceOrder(Command[Order, None]):
    order_id: str
    amount: float = 0.0


class GetOrder(Query[Order, Order | None]):
    order_id: str


# ---- ports ----


class EmailSender(Port):
    def send(self, to: str) -> None: ...


class SmtpSender(EmailSender):
    def send(self, to: str) -> None: ...


class FakeUnitOfWork(UnitOfWork):
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


# ---- handlers ----


class PlaceOrderHandler(CommandHandler[PlaceOrder]):
    session: Session | None = None

    def handle(self, command: PlaceOrder) -> None: ...


class GetOrderHandler(QueryHandler[GetOrder]):
    session: Session | None = None

    def handle(self, query: GetOrder) -> Order | None:
        return None


# ---- use case ----


class OrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]
    get_order: QueryPort[GetOrder]
    logger: Port
    email: EmailSender


# ---- skip unless flag is set ----

_run_integration = os.environ.get("RUN_INTEGRATION")


@pytest.mark.skipif(
    not _run_integration,
    reason="Set RUN_INTEGRATION=1 to run integration tests",
)
class TestRealGeneration:
    """Generates a full zensical site to a temp dir and validates the output."""

    def test_generates_all_files(self, tmp_path: Path) -> None:
        bc = BoundedContext(
            aggregate_roots=[Order],
            use_cases=[OrderUseCase],
            name="Orders",
        )
        infra = Infrastructure(
            handlers=[PlaceOrderHandler, GetOrderHandler],
            ports=[FakeUnitOfWork, SmtpSender],
        )
        mod = Module(name="orders", context=bc, infrastructure=infra)
        app = App(name="MyApp", modules=[mod], description="App description")

        doc = AutoDoc(app, tmp_path, site_name="MyApp Docs")
        doc.generate()

        self._assert_structure(tmp_path)
        self._assert_toml(tmp_path)
        self._assert_home(tmp_path)
        self._assert_bc_pages(tmp_path)

    @staticmethod
    def _assert_structure(root: Path) -> None:
        assert (root / "zensical.toml").is_file()
        assert (root / "docs/index.md").is_file()
        assert (root / "docs/bounded-contexts/orders/index.md").is_file()
        assert (root / "docs/bounded-contexts/orders/glossary.md").is_file()
        assert (root / "docs/bounded-contexts/orders/entities.md").is_file()
        assert (root / "docs/bounded-contexts/orders/infrastructure.md").is_file()
        assert (root / "docs/stylesheets/extra.css").is_file()
        assert (root / "docs/overrides/main.html").is_file()

    @staticmethod
    def _assert_toml(root: Path) -> None:
        content = root.joinpath("zensical.toml").read_text()
        config = tomllib.loads(content)
        assert config["site_name"] == "MyApp Docs"
        assert len(config["nav"]) == 2
        assert config["nav"][0] == {"Home": "index.md"}

    @staticmethod
    def _assert_home(root: Path) -> None:
        html = root.joinpath("docs/index.md").read_text()
        assert "MyApp Docs" in html
        assert "App description" in html
        assert "Orders" in html
        assert "home-hero" in html
        assert "feature-card" in html

    @staticmethod
    def _assert_bc_pages(root: Path) -> None:
        bc_index = root.joinpath("docs/bounded-contexts/orders/index.md").read_text()
        assert "Orders" in bc_index
        assert "Use Cases" in bc_index
        assert "OrderUseCase" in bc_index
        assert "Glossary" in bc_index

        glossary = root.joinpath("docs/bounded-contexts/orders/glossary.md").read_text()
        assert "Order" in glossary
        assert "OrderId" in glossary

        entities = root.joinpath("docs/bounded-contexts/orders/entities.md").read_text()
        assert "Order" in entities
        assert "OrderId" in entities

        infra = root.joinpath("docs/bounded-contexts/orders/infrastructure.md").read_text()
        assert "PlaceOrderHandler" in infra
        assert "GetOrderHandler" in infra
        assert "Sessions" in infra

    def test_content_non_empty(self, tmp_path: Path) -> None:
        bc = BoundedContext(aggregate_roots=[Order], name="Test")
        infra = Infrastructure()
        mod = Module(name="test", context=bc, infrastructure=infra)
        app = App(name="App", modules=[mod])
        doc = AutoDoc(app, tmp_path)
        doc.generate()

        for md in tmp_path.rglob("*.md"):
            assert len(md.read_text()) > 0
        assert len(tmp_path.joinpath("zensical.toml").read_text()) > 0

    def test_user_assets_preserved(self, tmp_path: Path) -> None:
        custom_css = tmp_path / "docs" / "stylesheets" / "extra.css"
        custom_css.parent.mkdir(parents=True)
        custom_css.write_text("/* user css */")

        custom_logo = tmp_path / "img" / "logo.png"
        custom_logo.parent.mkdir(parents=True)
        custom_logo.write_text("fake png")

        bc = BoundedContext(aggregate_roots=[Order], name="X")
        infra = Infrastructure()
        mod = Module(name="x", context=bc, infrastructure=infra)
        app = App(name="X", modules=[mod])
        doc = AutoDoc(app, tmp_path)
        doc.generate()

        assert custom_css.read_text() == "/* user css */"
        assert custom_logo.read_text() == "fake png"
