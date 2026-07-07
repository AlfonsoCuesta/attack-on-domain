from __future__ import annotations

from aod._internal.infrastructure.container import AdapterContainer
from aod._internal.testing.doubles.infrastructure.container import spy_adapter_container
from aod.application import Port
from aod._internal.infrastructure.session import Session


class _CustomPort(Port):
    value: str = "default"


def test_get_port_stub_cached() -> None:
    container = spy_adapter_container(AdapterContainer(weather=_CustomPort()))
    first = container.get_port_stub("weather")
    second = container.get_port_stub("weather")
    assert first is second


def test_get_session_stub_cached() -> None:
    container = spy_adapter_container(AdapterContainer(weather=_CustomPort()))
    first = container.get_session_stub(Session)
    second = container.get_session_stub(Session)
    assert first is second
