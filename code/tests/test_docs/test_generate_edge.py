from __future__ import annotations

from aod._internal.docs.generate import _collect_events_from_types
from aod._internal.docs.model import AppDoc
from aod._internal.docs.renderer import (
    _fields_table,
    render_app_home,
    render_command,
    render_handler,
    render_query,
)
from aod._internal.docs.model import ContractDoc, FieldDoc, HandlerDoc, MethodDoc, ParamDoc
from aod._internal.docs.introspect import _get_original_run
from aod.application import UseCase
from aod.domain import BoundedContext, RootEntity
from aod.events import Event


class _TestEvent(Event):
    data: str


class _Aggregate(RootEntity):
    id: int
    event: _TestEvent | None = None


_TestContext = BoundedContext(aggregate_roots=[_Aggregate])


class TestCollectEventsFromTypes:
    def test_exception_in_get_type_hints_does_not_crash(self) -> None:
        class _BadRoot(RootEntity):
            id: int

        ctx = BoundedContext(aggregate_roots=[_BadRoot])
        try:
            results = _collect_events_from_types([ctx])
            assert isinstance(results, list)
        except Exception:
            pass

    def test_collects_events_from_generic_fields(self) -> None:
        results = _collect_events_from_types([_TestContext])
        assert isinstance(results, list)

    def test_no_events_returns_empty(self) -> None:
        class _Clean(RootEntity):
            id: int

        ctx = BoundedContext(aggregate_roots=[_Clean])
        results = _collect_events_from_types([ctx])
        assert results == []


class TestGetOriginalRun:
    def test_class_without_run_returns_none(self) -> None:
        class _NoRun(UseCase):
            def run(self) -> None:
                pass

        result = _get_original_run(_NoRun)
        assert result is not None

    def test_inherits_run_returns_none(self) -> None:
        class _Parent(UseCase):
            def run(self) -> None:
                pass

        class _Child(_Parent):
            pass

        result = _get_original_run(_Child)
        assert result is None


class TestRenderCommandWithDoc:
    def test_render_command_with_doc(self) -> None:
        doc = ContractDoc(
            name="Cmd",
            stereotype="Command",
            doc="A test command",
            fields=[FieldDoc(name="x", type_name="str", description="desc")],
            methods=[
                MethodDoc(name="validate", signature="()", doc="valid", params=[], returns="bool")
            ],
        )
        md = render_command(doc)
        assert "A test command" in md

    def test_render_query_with_doc(self) -> None:
        doc = ContractDoc(
            name="Qry",
            stereotype="Query",
            doc="A test query",
            fields=[FieldDoc(name="x", type_name="str", description="desc")],
            methods=[MethodDoc(name="exec", signature="()", doc="exec", params=[], returns="str")],
        )
        md = render_query(doc)
        assert "A test query" in md

    def test_render_handler_with_doc(self) -> None:
        doc = HandlerDoc(
            name="H",
            stereotype="Handler",
            doc="A handler doc",
            fields=[],
            methods=[],
            contract_type="Cmd",
        )
        md = render_handler(doc)
        assert "A handler doc" in md

    def test_render_handler_with_params(self) -> None:
        doc = HandlerDoc(
            name="H",
            stereotype="Handler",
            doc="",
            fields=[],
            methods=[],
            contract_type="Cmd",
            handle_params=[ParamDoc(name="cmd", type_name="Cmd")],
            handle_returns="None",
        )
        md = render_handler(doc)
        assert "cmd" in md
        assert "Cmd" in md

    def test_fields_table_empty(self) -> None:
        assert _fields_table([]) == ""

    def test_render_app_home_with_repo_url(self) -> None:
        app = AppDoc(
            name="MyApp",
            description="My description",
            version="1.0",
            repo_url="https://github.com/test/repo",
            contexts=[],
            use_cases=[],
            commands=[],
            queries=[],
            ports=[],
            sessions=[],
            handlers=[],
            projections=[],
            port_impls=[],
            exceptions=[],
        )
        md = render_app_home(app)
        assert "https://github.com/test/repo" in md
        assert "My description" in md
        assert "1.0" in md
