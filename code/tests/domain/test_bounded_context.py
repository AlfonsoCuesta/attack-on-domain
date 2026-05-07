import pytest
from domain.bounded_context import BoundedContext
from domain.entity import Entity, RootEntity
from domain.service import Service


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

    with pytest.raises(ValueError, match="is not an Entity"):
        BoundedContext([NotEntity])  # type: ignore[list-item]


def test_bounded_context_rejects_non_root_entity() -> None:
    class NotRoot(Entity):
        id: int

    with pytest.raises(ValueError, match="is not a root Entity"):
        BoundedContext([NotRoot])  # type: ignore[list-item]


def test_bounded_context_rejects_entity_instance() -> None:
    class Order(RootEntity):
        id: int

    order = Order(id=1)

    with pytest.raises(TypeError):
        BoundedContext([order])  # type: ignore[list-item]


def test_bounded_context_accepts_services_too() -> None:
    class Order(RootEntity):
        id: int

    class Pricing(Service):
        pass

    bc = BoundedContext([Order], [Pricing])

    assert bc.aggregate_roots == (Order,)
    assert bc.services == (Pricing,)
