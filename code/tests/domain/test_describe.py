import functools
from types import SimpleNamespace

from aod._internal.domain.app import App
from aod._internal.domain.bounded_context import BoundedContext
from aod._internal.domain.describe import extract_fields
from aod._internal.domain.describe import extract_methods
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.entity_id import EntityId
from aod._internal.domain.service import Service
from aod._internal.domain.value_object import ValueObject


class IntId(EntityId):
    value: int


class LineItem(Entity):
    id: IntId


class Address(ValueObject):
    street: str


class Order(RootEntity):
    id: IntId
    amount: float
    items: list[LineItem]
    shipping: Address

    def approve(self) -> None:
        pass


class PricingService(Service):
    def calculate(self, order: Order) -> float:
        return 0.0


def test_describe_includes_all_types() -> None:
    bc = BoundedContext(
        aggregate_roots=[Order],
        services=[PricingService],
        name="Sales",
    )

    docs = bc.describe()

    names = {d.name for d in docs}
    assert "Order" in names
    assert "LineItem" in names
    assert "Address" in names
    assert "PricingService" in names


def test_describe_sets_correct_stereotypes() -> None:
    bc = BoundedContext(aggregate_roots=[Order], services=[PricingService], name="Sales")

    docs = bc.describe()
    by_name = {d.name: d.stereotype for d in docs}

    assert by_name["Order"] == "RootEntity"
    assert by_name["LineItem"] == "Entity"
    assert by_name["Address"] == "ValueObject"
    assert by_name["PricingService"] == "Service"


def test_describe_includes_class_docstring() -> None:
    class Customer(RootEntity):
        """A customer of the store."""

        id: IntId

    bc = BoundedContext(aggregate_roots=[Customer])
    docs = bc.describe()

    customer_doc = next(d for d in docs if d.name == "Customer")
    assert customer_doc.doc == "A customer of the store."


def test_describe_returns_empty_doc_when_no_docstring() -> None:
    bc = BoundedContext(aggregate_roots=[Order])
    docs = bc.describe()

    order_doc = next(d for d in docs if d.name == "Order")
    assert order_doc.doc == ""


def test_describe_includes_fields() -> None:
    bc = BoundedContext(aggregate_roots=[Order])
    docs = bc.describe()

    order_doc = next(d for d in docs if d.name == "Order")
    field_names = {f.name for f in order_doc.fields}
    assert "id" in field_names
    assert "amount" in field_names


def test_describe_includes_public_methods() -> None:
    bc = BoundedContext(aggregate_roots=[Order])
    docs = bc.describe()

    order_doc = next(d for d in docs if d.name == "Order")
    method_names = {m.name for m in order_doc.methods}
    assert "approve" in method_names


def test_describe_skips_private_methods() -> None:
    class Product(RootEntity):
        id: IntId

        def _internal(self) -> None:
            pass

    bc = BoundedContext(aggregate_roots=[Product])
    docs = bc.describe()

    product_doc = next(d for d in docs if d.name == "Product")
    assert all(not m.name.startswith("_") for m in product_doc.methods)


def test_describe_method_includes_signature() -> None:
    bc = BoundedContext(aggregate_roots=[Order], services=[PricingService])
    docs = bc.describe()

    pricing_doc = next(d for d in docs if d.name == "PricingService")
    calc = next(m for m in pricing_doc.methods if m.name == "calculate")
    assert "order" in calc.signature


def test_describe_method_includes_method_docstring() -> None:
    class Shipment(RootEntity):
        id: IntId

        def deliver(self) -> None:
            """Marks the shipment as delivered."""

    bc = BoundedContext(aggregate_roots=[Shipment])
    docs = bc.describe()

    shipment_doc = next(d for d in docs if d.name == "Shipment")
    deliver = next(m for m in shipment_doc.methods if m.name == "deliver")
    assert deliver.doc == "Marks the shipment as delivered."


def test_app_describe_returns_dict_of_contexts() -> None:
    class Product(RootEntity):
        id: IntId

    catalog = BoundedContext(aggregate_roots=[Product], name="Catalog")
    app = App("MyApp", catalog)

    result = app.describe()

    assert "Catalog" in result
    assert len(result["Catalog"]) > 0


def test_app_describe_includes_all_contexts() -> None:
    class Product(RootEntity):
        id: IntId

    class Order(RootEntity):
        id: IntId

    catalog = BoundedContext(aggregate_roots=[Product], name="Catalog")
    sales = BoundedContext(aggregate_roots=[Order], name="Sales")
    app = App("MyApp", catalog, sales)

    result = app.describe()

    assert "Catalog" in result
    assert "Sales" in result


def test_extract_fields_on_non_model() -> None:
    class NotAModel:
        pass

    assert extract_fields(NotAModel) == []


def test_describe_skips_private_fields() -> None:
    class Product(RootEntity):
        id: IntId
        name: str

    docs = BoundedContext(aggregate_roots=[Product]).describe()
    product_doc = next(d for d in docs if d.name == "Product")
    assert all(not f.name.startswith("_") for f in product_doc.fields)


def test_extract_methods_skips_non_callable() -> None:
    class Mixed:
        def valid_method(self) -> None:
            pass

        not_callable: int = 42

    result = extract_methods(Mixed)
    assert len(result) == 1
    assert result[0].name == "valid_method"


def test_extract_methods_handles_signature_error() -> None:
    class ClassWithBad:
        def good_method(self) -> None:
            pass

        compute = functools.partial(int)

    result = extract_methods(ClassWithBad)
    names = {m.name for m in result}
    assert "good_method" in names
    assert "compute" in names
    bad = next(m for m in result if m.name == "compute")
    assert bad.signature == "(...)"


def test_extract_fields_with_null_annotation() -> None:
    class Item(Entity):
        id: IntId

    fi = Item.__model_fields__["id"]
    object.__setattr__(fi, "annotation", None)

    result = extract_fields(Item)
    assert all(f.name != "id" for f in result)


def test_extract_fields_skips_private() -> None:
    class Fake:
        pass

    Fake.__model_fields__ = {"_hidden": SimpleNamespace(annotation=str)}  # type: ignore

    result = extract_fields(Fake)
    assert result == []
