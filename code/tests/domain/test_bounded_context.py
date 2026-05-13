import pytest
from aod._internal.core.domain_exception import (
    ClassExpectedError,
    InvalidEntityTypeError,
    InvalidRootEntityTypeError,
)
from aod._internal.domain.bounded_context import BoundedContext
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.service import Service


def test_bounded_context_accepts_only_root_entities() -> None:
    class Order(RootEntity):
        id: int

    class Customer(Entity, root=True):
        id: int

    bc = BoundedContext([Order, Customer])  # type: ignore[list-item]

    assert bc.aggregate_roots == (Order, Customer)
    assert bc.services == ()


def test_bounded_context_rejects_non_entity_class() -> None:
    class NotEntity:
        pass

    with pytest.raises(InvalidEntityTypeError, match="is not an Entity"):
        BoundedContext([NotEntity])  # type: ignore[list-item]


def test_bounded_context_rejects_non_root_entity() -> None:
    class NotRoot(Entity):
        id: int

    with pytest.raises(
        InvalidRootEntityTypeError, match="is not a root Entity"
    ):
        BoundedContext([NotRoot])  # type: ignore[list-item]


def test_bounded_context_rejects_entity_instance() -> None:
    class Order(RootEntity):
        id: int

    order = Order(id=1)

    with pytest.raises(ClassExpectedError, match="aggregate root"):
        BoundedContext([order])  # type: ignore[list-item]


def test_bounded_context_accepts_services_too() -> None:
    class Order(RootEntity):
        id: int

    class Pricing(Service):
        pass

    bc = BoundedContext([Order], [Pricing])

    assert bc.aggregate_roots == (Order,)
    assert bc.services == (Pricing,)
