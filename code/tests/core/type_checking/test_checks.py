import pytest
from aod._internal.core.domain_exception import (
    InvalidNestedTypeError,
    InvalidServiceParameterError,
)
from aod._internal.core.type_checking.checks import (
    check_entity,
    check_root_entity,
    check_service,
    check_value_object,
)
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.service import Service
from aod._internal.domain.value_object import ValueObject


def test_check_entity_raises_on_root_entity_field() -> None:
    class Product(RootEntity):
        id: int

    class BadEntity(Entity):
        id: int
        product: Product

    with pytest.raises(InvalidNestedTypeError, match="'product'"):
        check_entity(BadEntity)


def test_check_entity_passes_with_entity_field() -> None:
    class LineItem(Entity):
        id: int

    class Order(Entity):
        id: int
        items: list[LineItem]

    check_entity(Order)  # Should not raise


def test_check_root_entity_raises_on_root_entity_field() -> None:
    class Product(RootEntity):
        id: int

    class Order(RootEntity):
        id: int
        product: Product

    with pytest.raises(InvalidNestedTypeError, match="'product'"):
        check_root_entity(Order)


def test_check_value_object_raises_on_entity_field() -> None:
    class Customer(Entity):
        id: int

    class BadVO(ValueObject):
        customer: Customer

    with pytest.raises(InvalidNestedTypeError, match="'customer'"):
        check_value_object(BadVO)


def test_check_value_object_raises_on_root_entity_field() -> None:
    class Product(RootEntity):
        id: int

    class BadVO(ValueObject):
        product: Product

    with pytest.raises(InvalidNestedTypeError, match="'product'"):
        check_value_object(BadVO)


def test_check_value_object_passes_with_primitives() -> None:
    class GoodVO(ValueObject):
        amount: int
        label: str

    check_value_object(GoodVO)  # Should not raise


def test_check_value_object_passes_with_nested_vos() -> None:
    class Money(ValueObject):
        amount: int

    class Price(ValueObject):
        total: Money

    check_value_object(Price)  # Should not raise


def test_check_service_raises_on_entity_param() -> None:
    class Customer(Entity):
        id: int

    class BadService(Service):
        def process(self, customer: Customer) -> None:
            pass

    with pytest.raises(InvalidServiceParameterError, match="'customer'"):
        check_service(BadService)


def test_check_service_raises_on_entity_return() -> None:
    class Customer(Entity):
        id: int

    class BadService(Service):
        def get(self) -> Customer:
            return Customer(id=1)

    with pytest.raises(InvalidServiceParameterError, match="return"):
        check_service(BadService)


def test_check_service_passes_with_root_entity_param() -> None:
    class Order(RootEntity):
        id: int

    class GoodService(Service):
        def process(self, order: Order) -> None:
            pass

    check_service(GoodService)  # Should not raise


def test_check_service_passes_with_value_object_param() -> None:
    class Address(ValueObject):
        street: str

    class GoodService(Service):
        def get(self, address: Address) -> int:
            return 0

    check_service(GoodService)  # Should not raise


def test_check_service_passes_with_custom_class_param() -> None:
    class Config:
        rate: float = 0.1

    class GoodService(Service):
        def apply(self, config: Config) -> float:
            return config.rate

    check_service(GoodService)  # Should not raise
