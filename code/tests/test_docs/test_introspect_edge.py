from __future__ import annotations

from functools import partial

from aod._internal.docs.introspect import (
    _extract_fields,
    _extract_methods,
    _extract_params,
    _get_original_run,
    _get_own_doc,
    introspect_handler,
)
from aod.application import Command, Query, UseCase
from aod.domain import RootEntity
from aod.infrastructure import CommandHandler


class User(RootEntity):
    id: int
    name: str


class GetUser(Query[User, User | None]):
    user_id: int


class TestExtractFields:
    def test_private_field_skipped(self) -> None:
        class _HasPrivate(RootEntity):
            _internal: str = "x"
            public: str = "y"

        fields = _extract_fields(_HasPrivate)
        names = [f.name for f in fields]
        assert "public" in names
        assert "_internal" not in names


class TestExtractParams:
    def test_non_callable_returns_empty(self) -> None:
        params, returns = _extract_params(None)
        assert params == []
        assert returns == ""


class TestExtractMethods:
    def test_empty_class_returns_no_methods(self) -> None:
        class _Empty:
            pass

        result = _extract_methods(_Empty)
        assert result == []

    def test_non_callable_attribute_skipped(self) -> None:
        class _HasAttr:
            x = 42

        result = _extract_methods(_HasAttr)
        assert result == []

    def test_value_error_from_signature_returns_placeholder(self) -> None:
        class _WithPartial:
            m = partial(int, base=16)

        result = _extract_methods(_WithPartial)
        assert len(result) >= 1
        assert result[0].signature == "(...)"


class TestGetOwnDoc:
    def test_no_doc_returns_empty(self) -> None:
        class _NoDoc:
            pass

        assert _get_own_doc(_NoDoc) == ""

    def test_doc_matches_some_base(self) -> None:
        class _A:
            """Shared doc."""

        class _B(_A):
            """Shared doc."""

        doc = _get_own_doc(_B)
        assert doc == "Shared doc."


class TestGetOriginalRun:
    def test_non_use_case_without_run_returns_none(self) -> None:
        class _NoRun:
            pass

        result = _get_original_run(_NoRun)
        assert result is None

    def test_non_use_case_with_run_reaches_mro_return(self) -> None:
        class _NotUseCase:
            def run(self) -> None:
                pass

        result = _get_original_run(_NotUseCase)
        assert result is not None

    def test_non_use_case_finds_parent_run(self) -> None:
        class _Parent:
            def run(self) -> None:
                pass

        class _Child(_Parent):
            def run(self) -> None:
                pass

        result = _get_original_run(_Child)
        assert result is not None

    def test_use_case_returns_original(self) -> None:
        class _UC(UseCase):
            def run(self) -> None:
                pass

        result = _get_original_run(_UC)
        assert result is not None


class TestIntrospectHandler:
    def test_handler_without_base_handler_still_finds_contract(self) -> None:
        class _Cmd(Command[User, None]):
            user_id: int

        class _CustomHandler(CommandHandler[_Cmd]):
            def handle(self, command: _Cmd) -> None:
                return None

        doc = introspect_handler(_CustomHandler)
        assert doc.contract_type != ""
        assert doc.stereotype == "Handler"
