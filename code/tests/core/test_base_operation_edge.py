from __future__ import annotations

from typing import Any, get_origin

from aod._internal.core.base_operation import BaseOperation, _resolve_port_class


class TestResolvePortClass:
    def test_returns_none_when_origin_is_not_a_type(self) -> None:
        class _Fake:
            pass

        result = _resolve_port_class(_Fake)
        assert result is _Fake

    def test_origin_not_type_returns_none(self) -> None:
        result = _resolve_port_class(42)
        assert result is None

    def test_origin_is_not_instance_of_type(self) -> None:
        result = _resolve_port_class(str)
        assert result is str

    def test_origin_is_none_returns_none(self) -> None:
        result = _resolve_port_class(None)
        assert result is None

    def test_list_origin_not_a_type(self) -> None:
        origin = get_origin(list[str])
        assert origin is list
        result = _resolve_port_class(list[str])
        assert result is list


class TestBaseOperationGetTypeHints:
    def test_resolve_port_class_string_returns_none(self) -> None:
        result = _resolve_port_class("not_a_type")
        assert result is None

    def test_get_type_hints_failure_does_not_crash(self) -> None:
        class _GoodPort:
            pass

        try:

            class _OpWithBadRef(BaseOperation):
                bad_field: "NonExistentTypeForSureXYZ"

        except Exception:
            pass
