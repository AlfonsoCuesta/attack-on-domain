from __future__ import annotations

import pytest
from aod._internal.core.infrastructure_exception import PortNotFoundError
from aod._internal.infrastructure.container import AdapterContainer, extract_port_type
from aod._internal.application.handler import CommandPort
from aod.application import Command, Port, UseCase
from aod.domain import RootEntity


class _CustomPort(Port):
    value: str = "default"


class _Entity(RootEntity):
    id: int


class _Cmd(Command[_Entity, None]):
    x: str


class _CustomPortUseCase(UseCase):
    my_port: _CustomPort

    def run(self) -> None:
        pass


class _PortContainer(AdapterContainer):
    my_port: _CustomPort


class _UseCase(UseCase):
    my_port: _CustomPort

    def run(self) -> None:
        pass


class TestExtractPortType:
    def test_handler_protocol_is_excluded(self) -> None:
        result = extract_port_type(CommandPort[_Cmd])
        assert result is None


class TestInjectAdapters:
    def test_raises_when_port_not_found(self) -> None:
        class _EmptyContainer(AdapterContainer):
            pass

        container = _EmptyContainer()
        with pytest.raises(PortNotFoundError):
            container.adapt_use_case(_CustomPortUseCase)

    def test_with_custom_port_works(self) -> None:
        container = _PortContainer(my_port=_CustomPort())
        uc = container.adapt_use_case(_UseCase)
        assert isinstance(uc.my_port, _CustomPort)
