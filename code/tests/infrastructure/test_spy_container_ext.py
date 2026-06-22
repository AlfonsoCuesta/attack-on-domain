from __future__ import annotations

from aod._internal.infrastructure.container import AdapterContainer
from aod._internal.testing.doubles.infrastructure.container import spy_adapter_container
from aod.application import Port
from aod._internal.infrastructure.session import Session


class _CustomPort(Port):
    value: str = "default"


class _MyContainer(AdapterContainer):
    weather: _CustomPort


def test_get_port_stub_cached() -> None:
    container = spy_adapter_container(_MyContainer(weather=_CustomPort()))
    first = container.get_port_stub(_CustomPort)
    second = container.get_port_stub(_CustomPort)
    assert first is second


def test_get_session_stub_cached() -> None:
    container = spy_adapter_container(_MyContainer(weather=_CustomPort()))
    first = container.get_session_stub(Session)
    second = container.get_session_stub(Session)
    assert first is second


def test_get_port_instance_returns_stub_for_matching_type() -> None:
    container = spy_adapter_container(_MyContainer(weather=_CustomPort()))
    stub = container.get_port_stub(_CustomPort)
    result = container._get_port_instance(_CustomPort)
    assert result is stub
