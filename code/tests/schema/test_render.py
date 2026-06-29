"""Tests for AutoDoc — no filesystem I/O, overrides _write with a spy."""

from __future__ import annotations

from pathlib import Path

import pytest
from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler import (
    AsyncCommandPort,
    AsyncQueryPort,
    CommandPort,
    QueryPort,
)
from aod._internal.application.port import Port
from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.service import Service
from aod._internal.domain.value_object import ValueObject
from aod._internal.infrastructure.handlers import AsyncCommandHandler, CommandHandler, QueryHandler
from aod._internal.infrastructure.projection import (
    AsyncProjection,
    Projection,
    ReadProjection,
    WriteProjection,
)
from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.schema.app import App
from aod._internal.schema.bounded_context import BoundedContext
from aod._internal.schema.infrastructure import Infrastructure
from aod._internal.schema.module import Module
from aod._internal.schema.render import AutoDoc
from aod.domain import Field

# ============================================================
# Domain types
# ============================================================


class Address(ValueObject):
    street: str
    city: str


class Order(RootEntity):
    id: str = Field(id=True)
    total: float = 0.0
    shipping_address: Address

    def apply_discount(self, factor: float) -> None: ...


class LineItem(Entity):
    id: int = Field(id=True)
    product: str
    quantity: int


class PricingService(Service):
    def calculate_total(self, base: float) -> float:
        return base * 1.1


# ============================================================
# Contracts
# ============================================================


class PlaceOrder(Command[Order, None]):
    order_id: str
    amount: float = 0.0


class GetOrder(Query[Order, Order | None]):
    order_id: str


# ============================================================
# Ports
# ============================================================


class EmailSender(Port):
    def send(self, to: str) -> None: ...


class AnalyticsClient(Port):
    def track(self, event: str) -> None: ...


# ============================================================
# Port implementations
# ============================================================


class SmtpSender(EmailSender):
    def send(self, to: str) -> None: ...


class FakeAnalytics(AnalyticsClient):
    def track(self, event: str) -> None: ...


# ============================================================
# Use Cases
# ============================================================


class OrderUseCase(UseCase):
    place_order: CommandPort[PlaceOrder]
    get_order: QueryPort[GetOrder]
    logger: Port
    email: EmailSender


class NoopUseCase(UseCase):
    pass


class AsyncOrderUseCase(AsyncUseCase):
    place_order: AsyncCommandPort[PlaceOrder]
    get_order: AsyncQueryPort[GetOrder]
    logger: Port
    email: EmailSender


# ============================================================
# Handlers
# ============================================================


class PlaceOrderHandler(CommandHandler[PlaceOrder]):
    session: Session | None = None

    def handle(self, command: PlaceOrder) -> None: ...


class GetOrderHandler(QueryHandler[GetOrder]):
    session: Session | None = None

    def handle(self, query: GetOrder) -> Order | None:
        return None


class AsyncPlaceOrderHandler(AsyncCommandHandler[PlaceOrder]):
    session: AsyncSession | None = None

    async def handle(self, command: PlaceOrder) -> None: ...


# ============================================================
# Projections — inherits session from base, don't redeclare
# ============================================================


class OrderSummaryProjection(ReadProjection):
    def read(self, model: object) -> list[dict]:
        return []


class WriteOrderProjection(WriteProjection):
    def write(self, model: object) -> None: ...


class FullOrderProjection(Projection):
    def read(self, model: object) -> list[dict]:
        return []

    def write(self, model: object) -> None: ...


class AsyncOrderProjection(AsyncProjection):
    async def read(self, model: object) -> list[dict]:
        return []

    async def write(self, model: object) -> None: ...


# ============================================================
# Fixtures
# ============================================================


def _make_spy(d: AutoDoc) -> list[tuple[Path, str]]:
    captured: list[tuple[Path, str]] = []

    def write_spy(path: Path, content: str) -> None:
        captured.append((path, content))

    d._write = write_spy  # ty: ignore[invalid-assignment]

    def copy_spy(_dst_dir: Path, _dst_name: str, _src_rel: str) -> None:
        captured.append((_dst_dir / _dst_name, ""))

    d._copy_default_asset = copy_spy  # ty: ignore[invalid-assignment]
    return captured


@pytest.fixture
def doc_spy() -> tuple[AutoDoc, list[tuple[Path, str]]]:
    """Single-module AutoDoc with write spy."""
    bc = BoundedContext(
        aggregate_roots=[Order],
        use_cases=[OrderUseCase],
        name="Orders",
    )
    infra = Infrastructure(
        handlers=[PlaceOrderHandler, GetOrderHandler],
        ports=[SmtpSender],
    )
    mod = Module(name="orders", context=bc, infrastructure=infra)
    app = App(name="TestApp", modules=[mod], description="Test app description")
    d = AutoDoc(app, "/out")
    captured = _make_spy(d)
    return d, captured


@pytest.fixture
def doc_proj_spy() -> tuple[AutoDoc, list[tuple[Path, str]]]:
    """Single-module AutoDoc with projections."""
    bc = BoundedContext(
        aggregate_roots=[Order],
        use_cases=[OrderUseCase],
        name="Orders",
    )
    infra = Infrastructure(
        handlers=[PlaceOrderHandler, GetOrderHandler],
        projections=[OrderSummaryProjection, WriteOrderProjection, FullOrderProjection],
        ports=[SmtpSender],
    )
    mod = Module(name="orders", context=bc, infrastructure=infra)
    app = App(name="TestApp", modules=[mod], description="Test")
    d = AutoDoc(app, "/out")
    captured = _make_spy(d)
    return d, captured


# ============================================================
# Home page
# ============================================================


class TestHome:
    def test_with_modules(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, _ = doc_spy
        html = d._render_home()
        assert "TestApp" in html
        assert "Test app description" in html
        assert "orders" in html
        assert "bounded-contexts/orders/" in html
        assert "home-hero" in html
        assert "home-features" in html
        assert "feature-card" in html

    def test_without_modules(self) -> None:
        app = App(name="Empty", modules=[])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        html = d._render_home()
        assert "Empty" in html
        assert "home-features" not in html
        assert "feature-card" not in html

    def test_without_description(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order])
        infra = Infrastructure()
        mod = Module(name="orders", context=bc, infrastructure=infra)
        app = App(name="NoDesc", modules=[mod])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        html = d._render_home()
        assert "NoDesc" in html
        assert "description" not in html

    def test_multiple_modules(self) -> None:
        bc1 = BoundedContext(aggregate_roots=[Order], name="Orders")
        bc2 = BoundedContext(name="Sales")
        infra1 = Infrastructure()
        infra2 = Infrastructure()
        mod1 = Module(name="orders", context=bc1, infrastructure=infra1)
        mod2 = Module(name="sales", context=bc2, infrastructure=infra2)
        app = App(name="Multi", modules=[mod1, mod2])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        html = d._render_home()
        assert html.count("feature-card") == 2
        assert "orders" in html
        assert "sales" in html

    def test_site_name_override(self) -> None:
        app = App(name="RealName", modules=[], description="Desc")
        d = AutoDoc(app, "/out", site_name="Custom Name")
        _make_spy(d)
        html = d._render_home()
        assert "Custom Name" in html
        assert "RealName" not in html

    def test_site_description_override(self) -> None:
        app = App(name="X", modules=[], description="Original")
        d = AutoDoc(app, "/out", site_description="Custom desc")
        _make_spy(d)
        html = d._render_home()
        assert "Custom desc" in html
        assert "Original" not in html


# ============================================================
# BoundedContext page
# ============================================================


class TestBoundedContextPage:
    def test_basic_structure(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, _ = doc_spy
        mod = d.modules[0]
        html = d._render_bc_page(mod)
        assert "Orders" in html
        assert "Glossary" in html
        assert "Domain Entities" in html
        assert "Infrastructure" in html
        assert "feature-card" in html

    def test_use_cases(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, _ = doc_spy
        mod = d.modules[0]
        html = d._render_bc_page(mod)
        assert "Use Cases" in html
        assert "OrderUseCase" in html
        assert "CommandPort[PlaceOrder]" in html
        assert "QueryPort[GetOrder]" in html

    def test_projections(self, doc_proj_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, _ = doc_proj_spy
        mod = d.modules[0]
        html = d._render_bc_page(mod)
        assert "Projections" in html
        assert "OrderSummaryProjection" in html
        assert "WriteOrderProjection" in html
        assert "FullOrderProjection" in html

    def test_no_use_cases(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order])
        infra = Infrastructure()
        mod = Module(name="empty", context=bc, infrastructure=infra)
        app = App(name="Empty", modules=[mod])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        html = d._render_bc_page(d.modules[0])
        assert "Use Cases" not in html

    def test_no_projections(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, _ = doc_spy
        html = d._render_bc_page(d.modules[0])
        assert "Projections" not in html


# ============================================================
# Glossary
# ============================================================


class TestGlossary:
    def test_all_types(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, _ = doc_spy
        mod = d.modules[0]
        html = d._render_glossary(mod)
        assert "Root Entities" in html
        assert "Order" in html
        assert "Value Objects" in html
        assert "Address" in html

    def test_empty_domain(self) -> None:
        bc = BoundedContext(name="empty")
        infra = Infrastructure()
        mod = Module(name="empty", context=bc, infrastructure=infra)
        app = App(name="Empty", modules=[mod])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        html = d._render_glossary(d.modules[0])
        assert "No domain types defined" in html

    def test_with_services(self) -> None:
        bc = BoundedContext(
            aggregate_roots=[Order],
            services=[PricingService],
        )
        infra = Infrastructure()
        mod = Module(name="full", context=bc, infrastructure=infra)
        app = App(name="Full", modules=[mod])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        html = d._render_glossary(d.modules[0])
        assert "Root Entities" in html
        assert "Address" in html
        assert "Services" in html
        assert "PricingService" in html


# ============================================================
# Entities detail
# ============================================================


class TestEntities:
    def test_root_entity_fields_methods(
        self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]
    ) -> None:
        d, _ = doc_spy
        html = d._render_entities(d.modules[0])
        assert "Order" in html
        assert "Fields" in html
        assert "Methods" in html

    def test_value_objects(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, _ = doc_spy
        html = d._render_entities(d.modules[0])
        assert "Address" in html

    def test_empty(self) -> None:
        bc = BoundedContext(name="empty")
        infra = Infrastructure()
        mod = Module(name="empty", context=bc, infrastructure=infra)
        app = App(name="Empty", modules=[mod])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        html = d._render_entities(d.modules[0])
        assert "No domain entities defined" in html

    def test_with_services(self) -> None:
        bc = BoundedContext(
            aggregate_roots=[Order],
            services=[PricingService],
        )
        infra = Infrastructure()
        mod = Module(name="full", context=bc, infrastructure=infra)
        app = App(name="Full", modules=[mod])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        html = d._render_entities(d.modules[0])
        assert "PricingService" in html


# ============================================================
# Infrastructure detail
# ============================================================


class TestInfrastructure:
    def test_handlers(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, _ = doc_spy
        html = d._render_infrastructure(d.modules[0])
        assert "Handlers" in html
        assert "PlaceOrderHandler" in html
        assert "GetOrderHandler" in html
        assert "CommandHandler" in html
        assert "QueryHandler" in html

    def test_sessions(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, _ = doc_spy
        html = d._render_infrastructure(d.modules[0])
        assert "Sessions" in html

    def test_ports(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, _ = doc_spy
        html = d._render_infrastructure(d.modules[0])
        assert "Ports" in html

    def test_projections(self, doc_proj_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, _ = doc_proj_spy
        html = d._render_infrastructure(d.modules[0])
        assert "Projections" in html
        assert "OrderSummaryProjection" in html
        assert "WriteOrderProjection" in html
        assert "FullOrderProjection" in html

    def test_async_handler(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order])
        infra = Infrastructure(handlers=[AsyncPlaceOrderHandler])
        mod = Module(name="as", context=bc, infrastructure=infra)
        app = App(name="As", modules=[mod])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        html = d._render_infrastructure(d.modules[0])
        assert "Async" in html
        assert "AsyncPlaceOrderHandler" in html

    def test_empty(self) -> None:
        bc = BoundedContext(name="empty")
        infra = Infrastructure()
        mod = Module(name="empty", context=bc, infrastructure=infra)
        app = App(name="Empty", modules=[mod])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        html = d._render_infrastructure(d.modules[0])
        assert "No infrastructure defined" in html


# ============================================================
# Zensical config
# ============================================================


class TestZensicalConfig:
    def test_with_modules(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, _ = doc_spy
        toml = d._render_zensical_toml()
        assert "site_name" in toml
        assert "TestApp" in toml
        assert "navigation.tabs" in toml
        assert "[theme]" in toml
        assert "material" in toml
        assert "orders" in toml

    def test_without_modules(self) -> None:
        app = App(name="Empty", modules=[])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        toml = d._render_zensical_toml()
        assert "Bounded Contexts" not in toml

    def test_repo_url_included(self) -> None:
        app = App(name="X", modules=[])
        d = AutoDoc(app, "/out", repo_url="https://github.com/test")
        _make_spy(d)
        toml = d._render_zensical_toml()
        assert "github.com" in toml

    def test_site_description_in_config(self) -> None:
        app = App(name="X", modules=[], description="App desc")
        d = AutoDoc(app, "/out", site_description="Custom desc")
        _make_spy(d)
        toml = d._render_zensical_toml()
        assert "Custom desc" in toml


# ============================================================
# Nav formatting
# ============================================================


class TestNavFormatting:
    def test_simple(self) -> None:
        app = App(name="X", modules=[])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        nav = d._format_nav([{"Home": "index.md"}, {"Page": "page.md"}])
        assert "Home" in nav
        assert "index.md" in nav

    def test_nested(self) -> None:
        app = App(name="X", modules=[])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        nav = d._format_nav(
            [
                {"Home": "index.md"},
                {
                    "Section": [
                        "sub/index.md",
                        {"SubPage": "sub/page.md"},
                    ]
                },
            ]
        )
        assert "Section" in nav
        assert "SubPage" in nav
        assert "sub/index.md" in nav

    def test_string_items(self) -> None:
        app = App(name="X", modules=[])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        nav = d._format_nav(["a.md", "b.md"])
        assert "a.md" in nav


# ============================================================
# Full generate
# ============================================================


class TestGenerate:
    def test_files_written(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, captured = doc_spy
        d.generate()
        paths = [str(p) for p, _ in captured]
        assert any(p.endswith("zensical.toml") for p in paths)
        assert any(p.endswith("index.md") for p in paths)
        assert any(p.endswith("glossary.md") for p in paths)
        assert any(p.endswith("entities.md") for p in paths)
        assert any(p.endswith("infrastructure.md") for p in paths)
        assert any("extra.css" in p for p in paths)
        assert any("main.html" in p for p in paths)

    def test_content_not_empty(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, captured = doc_spy
        d.generate()
        md_files = [(p, c) for p, c in captured if p.suffix == ".md"]
        assert len(md_files) > 0
        for _, content in md_files:
            assert len(content) > 0

    def test_multiple_modules(self) -> None:
        bc1 = BoundedContext(aggregate_roots=[Order], name="Orders", use_cases=[OrderUseCase])
        bc2 = BoundedContext(name="Sales")
        infra1 = Infrastructure(handlers=[PlaceOrderHandler, GetOrderHandler], ports=[SmtpSender])
        infra2 = Infrastructure()
        mod1 = Module(name="orders", context=bc1, infrastructure=infra1)
        mod2 = Module(name="sales", context=bc2, infrastructure=infra2)
        app = App(name="Multi", modules=[mod1, mod2])
        d = AutoDoc(app, "/out")
        captured = _make_spy(d)
        d.generate()
        bc_dirs = {str(p).split("/")[-2] for p, _ in captured if "bounded-contexts" in str(p)}
        assert "orders" in bc_dirs
        assert "sales" in bc_dirs

    def test_exactly_one_config(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, captured = doc_spy
        d.generate()
        tomls = [(p, c) for p, c in captured if p.name == "zensical.toml"]
        assert len(tomls) == 1

    def test_exactly_one_home(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, captured = doc_spy
        d.generate()
        homes = [
            (p, c) for p, c in captured if p.name == "index.md" and "bounded-contexts" not in str(p)
        ]
        assert len(homes) == 1


# ============================================================
# AutoDoc construction
# ============================================================


class TestConstruction:
    def test_site_name_defaults_to_app_name(self) -> None:
        app = App(name="MyApp", modules=[])
        d = AutoDoc(app, "/out")
        assert d.site_name == "MyApp"

    def test_site_name_override(self) -> None:
        app = App(name="MyApp", modules=[])
        d = AutoDoc(app, "/out", site_name="Custom")
        assert d.site_name == "Custom"

    def test_repo_name_defaults_to_app_name(self) -> None:
        app = App(name="MyApp", modules=[])
        d = AutoDoc(app, "/out")
        assert d.repo_name == "MyApp"

    def test_output_dir_string(self) -> None:
        app = App(name="X", modules=[])
        d = AutoDoc(app, "some/path")
        assert str(d.output_dir) == "some/path"


# ============================================================
# Shared renderers
# ============================================================


class TestShared:
    def test_bc_description_full(self, doc_spy: tuple[AutoDoc, list[tuple[Path, str]]]) -> None:
        d, _ = doc_spy
        desc = d._bc_description(d.modules[0].domain)
        assert "root entity" in desc
        assert "value object" in desc
        assert "use case" in desc

    def test_bc_description_empty(self) -> None:
        bc = BoundedContext(name="empty")
        infra = Infrastructure()
        mod = Module(name="empty", context=bc, infrastructure=infra)
        app = App(name="X", modules=[mod])
        d = AutoDoc(app, "/out")
        desc = d._bc_description(d.modules[0].domain)
        assert desc == "No domain types defined"

    def test_render_field_table_empty(self) -> None:
        assert AutoDoc._render_field_table([]) == ""

    def test_render_param_table_empty(self) -> None:
        assert AutoDoc._render_param_table([]) == ""

    def test_render_field_table_content(self) -> None:
        from aod._internal.schema.docs.generic_docs import FieldDoc

        fields = [FieldDoc(name="id", type_name="int", default="0", description="The ID")]
        html = AutoDoc._render_field_table(fields)
        assert "id" in html
        assert "int" in html
        assert "The ID" in html

    def test_render_param_table_content(self) -> None:
        from aod._internal.schema.docs.generic_docs import ParamDoc

        params = [ParamDoc(name="x", type_name="str", default="''")]
        html = AutoDoc._render_param_table(params)
        assert "x" in html

    def test_render_method_block(self) -> None:
        from aod._internal.schema.docs.generic_docs import MethodDoc, ParamDoc

        m = MethodDoc(
            name="do_it",
            params=[ParamDoc(name="x", type_name="int")],
            return_type="str",
            description="Does it",
        )
        html = AutoDoc._render_method_block(m)
        assert "def" in html
        assert "do_it" in html

    def test_render_method_block_no_params(self) -> None:
        from aod._internal.schema.docs.generic_docs import MethodDoc

        m = MethodDoc(name="noop", return_type="None")
        html = AutoDoc._render_method_block(m)
        assert "def" in html

    def test_slug(self) -> None:
        assert AutoDoc._slug("Hello World") == "hello-world"
        assert AutoDoc._slug("Order") == "order"
        assert AutoDoc._slug("my-use_case") == "my-use-case"


# ============================================================
# Async use cases
# ============================================================


class TestAsyncUseCase:
    def test_async_use_case_in_home(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order], use_cases=[AsyncOrderUseCase], name="Async")
        infra = Infrastructure(
            handlers=[AsyncPlaceOrderHandler, GetOrderHandler], ports=[SmtpSender]
        )
        mod = Module(name="async-mod", context=bc, infrastructure=infra)
        app = App(name="AsyncApp", modules=[mod])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        html = d._render_bc_page(d.modules[0])
        assert "AsyncOrderUseCase" in html

    def test_async_handler_in_infra(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order])
        infra = Infrastructure(handlers=[AsyncPlaceOrderHandler])
        mod = Module(name="async", context=bc, infrastructure=infra)
        app = App(name="Async", modules=[mod])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        html = d._render_infrastructure(d.modules[0])
        assert "AsyncPlaceOrderHandler" in html
        assert "Async:" in html

    def test_async_projection_in_infra(self) -> None:
        bc = BoundedContext(aggregate_roots=[Order])
        infra = Infrastructure(projections=[AsyncOrderProjection])
        mod = Module(name="async", context=bc, infrastructure=infra)
        app = App(name="Async", modules=[mod])
        d = AutoDoc(app, "/out")
        _make_spy(d)
        html = d._render_infrastructure(d.modules[0])
        assert "AsyncOrderProjection" in html
        assert "Async" in html
