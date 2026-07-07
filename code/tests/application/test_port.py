from __future__ import annotations

from abc import abstractmethod

import pytest
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.core.event_emitter import Event
from aod.application import EventBus, Logger, Port, UnitOfWork, UseCase
from aod.testing.doubles import port_stub


class RestClientExample(Port):
    timeout: int = 30

    @abstractmethod
    def get(self, url: str) -> str: ...

    @abstractmethod
    def post(self, url: str, data: str) -> str: ...


class RealRestClient(RestClientExample):
    calls: list[str] = []

    def get(self, url: str) -> str:
        self.calls.append(f"GET {url}")
        return f"response for {url}"

    def post(self, url: str, data: str) -> str:
        self.calls.append(f"POST {url}: {data}")
        return f"created {url}"


def test_port_abstract_cannot_instantiate() -> None:
    with pytest.raises(TypeError):
        RestClientExample()


def test_concrete_port_instantiation() -> None:
    client = RealRestClient()
    assert client.timeout == 30


def test_port_methods_are_wrapped() -> None:
    client = RealRestClient()
    result = client.get("/users")
    assert result == "response for /users"
    assert list(client.calls) == ["GET /users"]


def test_port_methods_can_mutate_fields() -> None:
    client = RealRestClient(timeout=60)
    client.post("/items", '{"name": "test"}')
    assert client.timeout == 60


def test_port_mutation_blocked_outside_methods() -> None:
    client = RealRestClient()
    with pytest.raises(MutationForbiddenException):
        client.timeout = 99


def test_port_custom_field_validation() -> None:
    client = RealRestClient(timeout=42)
    assert client.timeout == 42


def test_port_as_use_case_field() -> None:
    class ApiUseCase(UseCase):
        client: RealRestClient

        def run(self) -> None:
            self.client.get("/status")
            self.client.post("/data", "x")

    client = RealRestClient()
    uc = ApiUseCase(client=client)
    uc.run()
    assert list(client.calls) == ["GET /status", "POST /data: x"]


def test_logger_abstract() -> None:
    with pytest.raises(TypeError):
        Logger()


def test_logger_concrete() -> None:
    log = port_stub(Logger)()
    log.info("hello", user_id=42)
    assert log.info.call_count == 1
    assert log.info.call_args_list[0].args == ("hello",)
    assert log.info.call_args_list[0].kwargs == {"user_id": 42}


def test_logger_debug() -> None:
    log = port_stub(Logger)()
    log.debug("debug msg", x=1)
    assert log.debug.call_count == 1
    assert log.debug.call_args_list[0].args == ("debug msg",)
    assert log.debug.call_args_list[0].kwargs == {"x": 1}


def test_logger_warning() -> None:
    log = port_stub(Logger)()
    log.warning("warn msg", y=2)
    assert log.warning.call_count == 1
    assert log.warning.call_args_list[0].args == ("warn msg",)
    assert log.warning.call_args_list[0].kwargs == {"y": 2}


def test_event_bus_abstract() -> None:
    with pytest.raises(TypeError):
        EventBus()


def test_event_bus_publish() -> None:
    bus = port_stub(EventBus)()
    e1 = Event()
    e2 = Event()
    bus.publish(e1, e2)
    assert bus.publish.call_count == 1
    assert len(bus.publish.call_args_list[0].args) == 2


def test_unit_of_work_abstract() -> None:
    with pytest.raises(TypeError):
        UnitOfWork()


def test_unit_of_work_commit() -> None:
    uow = port_stub(UnitOfWork)()
    uow.commit()
    assert uow.commit.called


def test_unit_of_work_rollback() -> None:
    uow = port_stub(UnitOfWork)()
    uow.rollback()
    assert uow.rollback.called
