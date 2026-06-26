import pytest
from aod._internal.core.domain_exception import DuplicateDomainTypeError
from aod._internal.domain.app import App
from aod._internal.domain.bounded_context import BoundedContext
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.entity_id import EntityId
from aod._internal.domain.service import Service
from aod._internal.domain.value_object import ValueObject
from aod.domain import Field


class IntId(EntityId):
    value: int


def test_app_accepts_single_context() -> None:
    class Order(RootEntity):
        id: IntId = Field(id=True)

    sales = BoundedContext(aggregate_roots=[Order], name="Sales")

    app = App("MyApp", sales)

    assert app.name == "MyApp"
    assert app.contexts == (sales,)


def test_app_accepts_multiple_non_overlapping_contexts() -> None:
    class Order(RootEntity):
        id: IntId = Field(id=True)

    class Product(RootEntity):
        id: IntId = Field(id=True)

    sales = BoundedContext(aggregate_roots=[Order], name="Sales")
    catalog = BoundedContext(aggregate_roots=[Product], name="Catalog")

    app = App("MyApp", sales, catalog)

    assert len(app.contexts) == 2


def test_app_rejects_duplicate_entity_across_contexts() -> None:
    class LineItem(Entity):
        id: IntId = Field(id=True)

    class Order(RootEntity):
        id: IntId = Field(id=True)
        items: list[LineItem]

    class Invoice(RootEntity):
        id: IntId = Field(id=True)
        lines: list[LineItem]

    ordering = BoundedContext(aggregate_roots=[Order], name="Ordering")
    billing = BoundedContext(aggregate_roots=[Invoice], name="Billing")

    with pytest.raises(
        DuplicateDomainTypeError,
        match="LineItem.*Entity.*already registered.*Ordering",
    ):
        App("MyApp", ordering, billing)


def test_app_rejects_duplicate_root_entity_across_contexts() -> None:
    class Product(RootEntity):
        id: IntId = Field(id=True)

    inventory = BoundedContext(aggregate_roots=[Product], name="Inventory")
    catalog = BoundedContext(aggregate_roots=[Product], name="Catalog")

    with pytest.raises(
        DuplicateDomainTypeError,
        match="Product.*Entity.*already registered.*Inventory",
    ):
        App("MyApp", inventory, catalog)


def test_app_rejects_duplicate_service_across_contexts() -> None:
    class Pricing(Service):
        pass

    sales = BoundedContext(services=[Pricing], name="Sales")
    billing = BoundedContext(services=[Pricing], name="Billing")

    with pytest.raises(
        DuplicateDomainTypeError,
        match="Pricing.*Service.*already registered.*Sales",
    ):
        App("MyApp", sales, billing)


def test_app_accepts_duplicate_value_object_across_contexts() -> None:
    class Address(ValueObject):
        street: str

    class Order(RootEntity):
        id: IntId = Field(id=True)
        shipping: Address

    class Customer(RootEntity):
        id: IntId = Field(id=True)
        address: Address

    sales = BoundedContext(aggregate_roots=[Order], name="Sales")
    crm = BoundedContext(aggregate_roots=[Customer], name="CRM")

    app = App("MyApp", sales, crm)

    assert len(app.contexts) == 2


def test_app_rejects_duplicate_discovered_entity_across_contexts() -> None:
    class TaxBreakdown(Entity):
        id: IntId = Field(id=True)
        rate: float

    class Order(RootEntity):
        id: IntId = Field(id=True)
        taxes: list[TaxBreakdown]

    class Invoice(RootEntity):
        id: IntId = Field(id=True)
        lines: list[TaxBreakdown]

    ordering = BoundedContext(aggregate_roots=[Order], name="Ordering")
    billing = BoundedContext(aggregate_roots=[Invoice], name="Billing")

    with pytest.raises(
        DuplicateDomainTypeError,
        match="TaxBreakdown.*Entity.*already registered.*Ordering",
    ):
        App("MyApp", ordering, billing)


def test_app_error_message_mentions_first_context() -> None:
    class Report(RootEntity):
        id: IntId = Field(id=True)

    analytics = BoundedContext(aggregate_roots=[Report], name="Analytics")
    reporting = BoundedContext(aggregate_roots=[Report], name="Reporting")

    with pytest.raises(DuplicateDomainTypeError) as exc_info:
        App("MyApp", analytics, reporting)

    assert "Report" in str(exc_info.value)
    assert "Analytics" in str(exc_info.value)
    assert "Reporting" not in str(exc_info.value)
