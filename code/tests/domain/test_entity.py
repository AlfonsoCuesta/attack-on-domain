from aod._internal.domain.entity import Entity, RootEntity


def test_entity_is_not_root() -> None:
    class A(Entity):
        x: int

    assert not issubclass(A, RootEntity)


def test_root_entity_is_root() -> None:
    class R(RootEntity):
        x: int

    assert issubclass(R, RootEntity)


def test_root_entity_inherits_entity() -> None:
    assert issubclass(RootEntity, Entity)
