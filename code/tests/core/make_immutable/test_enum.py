from __future__ import annotations

from enum import Enum, IntEnum, auto

from aod._internal.core.base_guarded.make_immutable.make_immutable import make_immutable


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Priority(IntEnum):
    LOW = 1
    HIGH = 2


class StrEnum(str, Enum):
    FOO = "foo"
    BAR = "bar"


def test_make_immutable_returns_enum_unchanged() -> None:
    assert make_immutable(Color.RED) is Color.RED


def test_make_immutable_returns_int_enum_unchanged() -> None:
    assert make_immutable(Priority.HIGH) is Priority.HIGH


def test_make_immutable_returns_str_enum_unchanged() -> None:
    assert make_immutable(StrEnum.FOO) is StrEnum.FOO


def test_make_immutable_enum_inside_list() -> None:
    result = make_immutable([Color.RED, Color.GREEN])
    assert list(result) == [Color.RED, Color.GREEN]


def test_make_immutable_enum_inside_dict() -> None:
    result = make_immutable({"color": Color.RED})
    assert result["color"] is Color.RED


def test_make_immutable_enum_inside_set() -> None:
    result = make_immutable({Color.RED, Color.GREEN})
    assert result == {Color.RED, Color.GREEN}


def test_make_immutable_flag_enum_unchanged() -> None:
    from enum import Flag

    class Perm(Flag):
        READ = auto()
        WRITE = auto()

    assert make_immutable(Perm.READ) is Perm.READ
    assert make_immutable(Perm.READ | Perm.WRITE) is Perm.READ | Perm.WRITE
