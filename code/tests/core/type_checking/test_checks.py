from unittest import mock

import pytest
from pydantic.fields import FieldInfo
from aod._internal.core.domain_exception import (
    InvalidNestedTypeError,
    InvalidServiceParameterError,
)
from aod._internal.core.type_handlers import BaseGuardedTypeHandler, ServiceTypeHandler
from aod._internal.core.type_handlers.generic_utils import (
    get_generic_arg_from_mro,
    get_last_generic_arg,
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
        BaseGuardedTypeHandler.check_entity(BadEntity)


def test_check_entity_passes_with_entity_field() -> None:
    class LineItem(Entity):
        id: int

    class Order(Entity):
        id: int
        items: list[LineItem]

    BaseGuardedTypeHandler.check_entity(Order)  # Should not raise


def test_check_root_entity_raises_on_root_entity_field() -> None:
    class Product(RootEntity):
        id: int

    class Order(RootEntity):
        id: int
        product: Product

    with pytest.raises(InvalidNestedTypeError, match="'product'"):
        BaseGuardedTypeHandler.check_root_entity(Order)


def test_check_value_object_raises_on_entity_field() -> None:
    class Customer(Entity):
        id: int

    class BadVO(ValueObject):
        customer: Customer

    with pytest.raises(InvalidNestedTypeError, match="'customer'"):
        BaseGuardedTypeHandler.check_value_object(BadVO)


def test_check_value_object_raises_on_root_entity_field() -> None:
    class Product(RootEntity):
        id: int

    class BadVO(ValueObject):
        product: Product

    with pytest.raises(InvalidNestedTypeError, match="'product'"):
        BaseGuardedTypeHandler.check_value_object(BadVO)


def test_check_value_object_passes_with_primitives() -> None:
    class GoodVO(ValueObject):
        amount: int
        label: str

    BaseGuardedTypeHandler.check_value_object(GoodVO)  # Should not raise


def test_check_value_object_passes_with_nested_vos() -> None:
    class Money(ValueObject):
        amount: int

    class Price(ValueObject):
        total: Money

    BaseGuardedTypeHandler.check_value_object(Price)  # Should not raise


def test_check_service_raises_on_entity_param() -> None:
    class Customer(Entity):
        id: int

    class BadService(Service):
        def process(self, customer: Customer) -> None:
            pass

    with pytest.raises(InvalidServiceParameterError, match="'customer'"):
        ServiceTypeHandler.check_service(BadService)


def test_check_service_raises_on_entity_return() -> None:
    class Customer(Entity):
        id: int

    class BadService(Service):
        def get(self) -> Customer:
            return Customer(id=1)

    with pytest.raises(InvalidServiceParameterError, match="return"):
        ServiceTypeHandler.check_service(BadService)


def test_check_service_passes_with_root_entity_param() -> None:
    class Order(RootEntity):
        id: int

    class GoodService(Service):
        def process(self, order: Order) -> None:
            pass

    ServiceTypeHandler.check_service(GoodService)  # Should not raise


def test_check_service_passes_with_value_object_param() -> None:
    class Address(ValueObject):
        street: str

    class GoodService(Service):
        def get(self, address: Address) -> int:
            return 0

    ServiceTypeHandler.check_service(GoodService)  # Should not raise


def test_check_service_passes_with_custom_class_param() -> None:
    class Config:
        rate: float = 0.1

    class GoodService(Service):
        def apply(self, config: Config) -> float:
            return config.rate

    ServiceTypeHandler.check_service(GoodService)  # Should not raise


# --- type_handlers/__init__.py coverage ---


def test_import_generic_utils_through_module() -> None:
    import aod._internal.core.type_handlers as handler_module

    func = handler_module.get_generic_arg_from_mro
    assert callable(func)

    func2 = handler_module.get_generic_arg_from_orig_bases
    assert callable(func2)

    func3 = handler_module.validate_generic_arg_is_subclass
    assert callable(func3)

    func4 = handler_module.validate_handler_subclass
    assert callable(func4)


def test_module_attribute_error() -> None:
    import aod._internal.core.type_handlers as handler_module

    with pytest.raises(AttributeError, match="has no attribute"):
        handler_module.nonexistent_attr  # type: ignore[attr-defined]


# --- base_guarded_handler.py coverage ---


def _add_model_field(cls: type, name: str, annotation: object) -> None:
    cls.__model_fields__[name] = FieldInfo(annotation=annotation)  # type: ignore


def test_check_entity_skips_private_fields() -> None:
    class MyEntity(Entity):
        id: int

    _add_model_field(MyEntity, "_private", int)
    BaseGuardedTypeHandler.check_entity(MyEntity)  # Should not raise


def test_check_entity_skips_none_annotation() -> None:
    class MyEntity(Entity):
        id: int

    _add_model_field(MyEntity, "public_none", None)
    BaseGuardedTypeHandler.check_entity(MyEntity)  # Should not raise


def test_check_value_object_skips_private_fields() -> None:
    class MyVO(ValueObject):
        value: str

    _add_model_field(MyVO, "_private", str)
    BaseGuardedTypeHandler.check_value_object(MyVO)  # Should not raise


def test_check_value_object_skips_none_annotation() -> None:
    class MyVO(ValueObject):
        value: str

    _add_model_field(MyVO, "public_none", None)
    BaseGuardedTypeHandler.check_value_object(MyVO)  # Should not raise


def test_discover_types_skips_private_fields_in_entity() -> None:
    class Inner(Entity):
        id: int

    _add_model_field(Inner, "_private", str)

    class Root(RootEntity):
        id: int
        inner: Inner

    entities, vos = BaseGuardedTypeHandler.discover_types([Root])
    assert Inner in entities


def test_discover_types_skips_none_annotation_in_entity() -> None:
    class Inner(Entity):
        id: int

    _add_model_field(Inner, "public_none", None)

    class Root(RootEntity):
        id: int
        inner: Inner

    entities, vos = BaseGuardedTypeHandler.discover_types([Root])
    assert Inner in entities


def test_discover_types_skips_class_without_model_fields() -> None:
    class NonPydantic:
        pass

    class Root(RootEntity):
        id: int

    entities, vos = BaseGuardedTypeHandler.discover_types([Root, NonPydantic])  # type: ignore
    assert isinstance(entities, list)
    assert isinstance(vos, list)


# --- service_handler.py coverage ---


def test_check_service_skips_param_without_annotation() -> None:
    class SomeService(Service):
        def process(self, x) -> None:  # type: ignore[no-untyped-def]
            pass

    ServiceTypeHandler.check_service(SomeService)  # Should not raise


def test_check_service_handles_bad_signature() -> None:
    class SomeService(Service):
        def process(self, x: int) -> None:
            pass

    with mock.patch(
        "aod._internal.core.type_handlers.service_handler.inspect.signature",
        side_effect=ValueError("no signature"),
    ):
        ServiceTypeHandler.check_service(SomeService)  # Should not raise


def test_check_service_handles_string_annotation() -> None:
    class SomeService(Service):
        def process(self, x: "int") -> None:  # noqa: F722
            pass

    ServiceTypeHandler.check_service(SomeService)  # Should not raise


def test_resolved_hints_exception() -> None:
    class SomeService(Service):
        def process(self, x: "int") -> None:  # noqa: F722
            pass

    with mock.patch(
        "aod._internal.core.type_handlers.service_handler.typing.get_type_hints",
        side_effect=RuntimeError("boom"),
    ):
        ServiceTypeHandler.check_service(SomeService)  # Should not raise


def test_get_generic_arg_from_mro_finds_arg() -> None:
    from typing import Generic, TypeVar

    T = TypeVar("T")

    class Base(Generic[T]):
        pass

    class Concrete(Base[int]):
        pass

    result = get_generic_arg_from_mro(Concrete, (Base,))
    assert result is int


def test_get_generic_arg_from_mro_returns_none_when_not_found() -> None:
    class Plain:
        pass

    result = get_generic_arg_from_mro(Plain, (int,))
    assert result is None


def test_get_last_generic_arg_finds_last_arg() -> None:
    from typing import Generic, TypeVar

    T = TypeVar("T")
    U = TypeVar("U")

    class Base(Generic[T, U]):
        pass

    class Concrete(Base[int, str]):
        pass

    result = get_last_generic_arg(Concrete)
    assert result is str


def test_get_last_generic_arg_returns_none_when_not_found() -> None:
    class Plain:
        pass

    result = get_last_generic_arg(Plain)
    assert result is None
