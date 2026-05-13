from aod._internal.domain.entity import Entity, RootEntity


def test_entity_is_not_root_by_default() -> None:
    class A(Entity):
        x: int

    assert A.is_root() is False


def test_entity_root_true_marks_as_root() -> None:
    class R(Entity, root=True):
        x: int

    assert R.is_root() is True


def test_entity_root_false_explicit_marks_as_not_root() -> None:
    class R(Entity, root=True):
        x: int

    class Child(R, root=False):
        y: int

    assert R.is_root() is True
    assert Child.is_root() is False


def test_root_entity_is_root() -> None:
    class R(RootEntity):
        x: int

    assert R.is_root() is True


def test_root_entity_inherits_entity() -> None:
    assert issubclass(RootEntity, Entity)
