import pytest
from aod._internal.core.domain_exception import (
    ClassExpectedError,
    InvalidEntityTypeError,
    InvalidNestedTypeError,
    InvalidRootEntityTypeError,
    InvalidServiceParameterError,
    InvalidServiceTypeError,
)
from aod._internal.domain.bounded_context import BoundedContext
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.service import Service
from aod._internal.domain.value_object import ValueObject


def test_bounded_context_accepts_only_root_entities() -> None:
    class Order(RootEntity):
        id: int

    class Customer(RootEntity):
        id: int

    bc = BoundedContext(aggregate_roots=[Order, Customer])

    assert bc.aggregate_roots == (Order, Customer)
    assert bc.services == ()
    assert bc.entities == ()
    assert bc.value_objects == ()


def test_bounded_context_rejects_non_entity_class() -> None:
    class NotEntity:
        pass

    with pytest.raises(InvalidEntityTypeError, match="is not an Entity"):
        BoundedContext(aggregate_roots=[NotEntity])  # type: ignore


def test_bounded_context_rejects_non_root_entity() -> None:
    class NotRoot(Entity):
        id: int

    with pytest.raises(InvalidRootEntityTypeError, match="is not a root Entity"):
        BoundedContext(aggregate_roots=[NotRoot])  # type: ignore


def test_bounded_context_rejects_entity_instance() -> None:
    class Order(RootEntity):
        id: int

    order = Order(id=1)

    with pytest.raises(ClassExpectedError, match="aggregate root"):
        BoundedContext(aggregate_roots=[order])  # type: ignore


def test_bounded_context_accepts_services_too() -> None:
    class Order(RootEntity):
        id: int

    class Pricing(Service):
        pass

    bc = BoundedContext(aggregate_roots=[Order], services=[Pricing])

    assert bc.aggregate_roots == (Order,)
    assert bc.services == (Pricing,)


def test_bounded_context_rejects_non_service_class() -> None:
    class NotService:
        pass

    with pytest.raises(InvalidServiceTypeError, match="is not a Service"):
        BoundedContext(services=[NotService])  # type: ignore


# ---------------------------------------------------------------------------
# Type discovery
# ---------------------------------------------------------------------------


def test_discovers_entity_from_root_entity_field() -> None:
    class LineItem(Entity):
        id: int

    class Order(RootEntity):
        id: int
        items: list[LineItem]

    bc = BoundedContext(aggregate_roots=[Order])

    assert Order in bc.aggregate_roots
    assert LineItem in bc.entities


def test_discovers_value_object_from_root_entity_field() -> None:
    class Address(ValueObject):
        street: str

    class Order(RootEntity):
        id: int
        shipping: Address

    bc = BoundedContext(aggregate_roots=[Order])

    assert Address in bc.value_objects


def test_discovers_nested_entities_recursively() -> None:
    class TaxBreakdown(Entity):
        id: int
        rate: float

    class LineItem(Entity):
        id: int
        taxes: list[TaxBreakdown]

    class Order(RootEntity):
        id: int
        items: list[LineItem]

    bc = BoundedContext(aggregate_roots=[Order])

    assert LineItem in bc.entities
    assert TaxBreakdown in bc.entities


def test_discovers_shared_value_object_only_once() -> None:
    class Money(ValueObject):
        amount: int

    class TaxLine(Entity):
        id: int
        total: Money

    class LineItem(Entity):
        id: int
        price: Money
        taxes: list[TaxLine]

    class Order(RootEntity):
        id: int
        items: list[LineItem]

    bc = BoundedContext(aggregate_roots=[Order])

    assert Money in bc.value_objects
    assert TaxLine in bc.entities
    assert LineItem in bc.entities
    assert len(bc.value_objects) == 1  # Money is only registered once


def test_root_entity_with_no_nested_types_has_empty_discovery() -> None:
    class Order(RootEntity):
        id: int

    bc = BoundedContext(aggregate_roots=[Order])

    assert bc.entities == ()
    assert bc.value_objects == ()


# ---------------------------------------------------------------------------
# entity field constraint: Entity cannot have RootEntity fields
# ---------------------------------------------------------------------------


def test_entity_with_root_entity_field_raises_error() -> None:
    class Product(RootEntity):
        id: int

    class OrderLine(Entity):
        id: int
        product: Product

    class Order(RootEntity):
        id: int
        lines: list[OrderLine]

    with pytest.raises(InvalidNestedTypeError, match="references 'Product'"):
        BoundedContext(aggregate_roots=[Order, Product])


def test_root_entity_with_root_entity_field_raises_error() -> None:
    class Product(RootEntity):
        id: int

    class Order(RootEntity):
        id: int
        product: Product

    with pytest.raises(InvalidNestedTypeError, match="references 'Product'"):
        BoundedContext(aggregate_roots=[Order, Product])


def test_entity_with_entity_field_is_allowed() -> None:
    class LineItem(Entity):
        id: int

    class Order(RootEntity):
        id: int
        items: list[LineItem]

    bc = BoundedContext(aggregate_roots=[Order])

    assert LineItem in bc.entities


def test_entity_with_value_object_field_is_allowed() -> None:
    class Address(ValueObject):
        street: str

    class Order(RootEntity):
        id: int
        shipping: Address

    BoundedContext(aggregate_roots=[Order])  # Should not raise


def test_entity_with_optional_root_entity_field_raises_error() -> None:
    class Product(RootEntity):
        id: int

    class OrderLine(Entity):
        id: int
        product: Product | None = None

    class Order(RootEntity):
        id: int
        lines: list[OrderLine]

    with pytest.raises(InvalidNestedTypeError, match="references 'Product'"):
        BoundedContext(aggregate_roots=[Order, Product])


def test_entity_with_list_of_root_entity_raises_error() -> None:
    class Product(RootEntity):
        id: int

    class OrderLine(Entity):
        id: int
        products: list[Product]

    class Order(RootEntity):
        id: int
        lines: list[OrderLine]

    with pytest.raises(InvalidNestedTypeError):
        BoundedContext(aggregate_roots=[Order, Product])


def test_root_entity_field_error_discovered_through_child_entity() -> None:
    """A nested Entity that references a RootEntity must also raise."""

    class Product(RootEntity):
        id: int

    class LineItem(Entity):
        id: int
        product: Product

    class Order(RootEntity):
        id: int
        items: list[LineItem]

    with pytest.raises(InvalidNestedTypeError, match="references 'Product'"):
        BoundedContext(aggregate_roots=[Order, Product])


# ---------------------------------------------------------------------------
# value_object field constraint: ValueObject cannot have Entity fields
# ---------------------------------------------------------------------------


def test_value_object_with_entity_field_raises_error() -> None:
    class Customer(Entity):
        id: int

    class OrderLineRef(ValueObject):
        customer: Customer

    class Order(RootEntity):
        id: int
        ref: OrderLineRef

    with pytest.raises(InvalidNestedTypeError, match="references 'Customer'"):
        BoundedContext(aggregate_roots=[Order])


def test_value_object_with_root_entity_field_raises_error() -> None:
    class Product(RootEntity):
        id: int

    class ProductRef(ValueObject):
        product: Product

    class Order(RootEntity):
        id: int
        ref: ProductRef

    with pytest.raises(InvalidNestedTypeError, match="references 'Product'"):
        BoundedContext(aggregate_roots=[Order])


def test_value_object_with_only_primitives_and_other_vos_is_allowed() -> None:
    class Money(ValueObject):
        amount: int

    class Price(ValueObject):
        total: Money
        tax: Money

    class Order(RootEntity):
        id: int
        price: Price

    bc = BoundedContext(aggregate_roots=[Order])

    assert Price in bc.value_objects
    assert Money in bc.value_objects


# ---------------------------------------------------------------------------
# service constraint
# ---------------------------------------------------------------------------


def test_service_with_entity_param_raises_error() -> None:
    class Customer(Entity):
        id: int

    class ValidationService(Service):
        def validate(self, customer: Customer) -> bool:
            return True

    with pytest.raises(InvalidServiceParameterError, match="'Customer'"):
        BoundedContext(
            services=[ValidationService],
        )


def test_service_with_value_object_param_is_allowed() -> None:
    class Address(ValueObject):
        street: str

    class ShippingService(Service):
        def calculate(self, address: Address) -> float:
            return 0.0

    bc = BoundedContext(
        services=[ShippingService],
    )

    assert bc.services == (ShippingService,)


def test_service_with_root_entity_param_is_allowed() -> None:
    class Order(RootEntity):
        id: int

    class PricingService(Service):
        def calculate(self, order: Order) -> float:
            return 0.0

    bc = BoundedContext(
        services=[PricingService],
        aggregate_roots=[Order],
    )

    assert bc.services == (PricingService,)


def test_service_with_custom_class_param_is_allowed() -> None:
    class DiscountConfig:
        rate: float = 0.1

    class PricingService(Service):
        def apply(self, config: DiscountConfig) -> float:
            return config.rate

    bc = BoundedContext(services=[PricingService])

    assert bc.services == (PricingService,)


def test_service_with_multiple_params_only_entity_forbidden() -> None:
    class Order(RootEntity):
        id: int

    class Customer(Entity):
        id: int

    class BadService(Service):
        def process(self, order: Order, customer: Customer) -> None:
            pass

    with pytest.raises(InvalidServiceParameterError, match="'customer'"):
        BoundedContext(
            services=[BadService],
            aggregate_roots=[Order],
        )


def test_bounded_context_rejects_service_instance() -> None:
    with pytest.raises(ClassExpectedError, match="service"):
        BoundedContext(services=["not_a_service"])  # type: ignore


def test_bounded_context_repr_without_name() -> None:
    bc = BoundedContext()
    result = repr(bc)
    assert result.startswith("<")


def test_service_with_entity_return_type_raises_error() -> None:
    class Customer(Entity):
        id: int

    class BadService(Service):
        def get_customer(self) -> Customer:
            return Customer(id=1)

    with pytest.raises(InvalidServiceParameterError, match="return"):
        BoundedContext(services=[BadService])


def test_service_with_root_entity_return_type_is_allowed() -> None:
    class Order(RootEntity):
        id: int

    class OrderService(Service):
        def get_order(self) -> Order:
            return Order(id=1)

    bc = BoundedContext(services=[OrderService], aggregate_roots=[Order])

    assert bc.services == (OrderService,)


def test_service_with_value_object_return_type_is_allowed() -> None:
    class Address(ValueObject):
        street: str

    class GeoService(Service):
        def get_address(self) -> Address:
            return Address(street="x")

    bc = BoundedContext(services=[GeoService])

    assert bc.services == (GeoService,)


def test_duplicate_root_entity_in_aggregate_roots() -> None:
    class Address(ValueObject):
        street: str

    class Customer(RootEntity):
        id: int
        address: Address

    bc = BoundedContext(aggregate_roots=[Customer, Customer])

    assert Address in bc.value_objects
