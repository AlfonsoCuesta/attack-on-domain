from __future__ import annotations

from abc import abstractmethod

import pytest
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.core.event_emitter import Event
from aod.application import EventBus, Logger, Port, UnitOfWork, UseCase
from aod.testing.doubles.application import SpyEventBus, SpyLogger, SpyUnitOfWork


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
        results: list[str] = []

        def run(self) -> None:
            r1 = self.client.get("/status")
            r2 = self.client.post("/data", "x")
            self.results = [r1, r2]

    uc = ApiUseCase(client=RealRestClient())
    uc.run()
    assert uc.results == ["response for /status", "created /data"]


def test_logger_abstract() -> None:
    with pytest.raises(TypeError):
        Logger()


def test_logger_concrete() -> None:
    log = SpyLogger()
    log.info("hello", user_id=42)
    assert len(log.entries) == 1
    assert log.entries[0].msg == "hello"
    assert log.entries[0].context == {"user_id": 42}


def test_logger_debug() -> None:
    log = SpyLogger()
    log.debug("debug msg", x=1)
    assert len(log.entries) == 1
    assert log.entries[0].level == "debug"
    assert log.entries[0].msg == "debug msg"
    assert log.entries[0].context == {"x": 1}


def test_logger_warning() -> None:
    log = SpyLogger()
    log.warning("warn msg", y=2)
    assert len(log.entries) == 1
    assert log.entries[0].level == "warning"
    assert log.entries[0].msg == "warn msg"
    assert log.entries[0].context == {"y": 2}


def test_event_bus_abstract() -> None:
    with pytest.raises(TypeError):
        EventBus()  # type: ignore[abstract]


def test_event_bus_publish() -> None:
    bus = SpyEventBus()
    e1 = Event()
    e2 = Event()
    bus.publish(e1, e2)
    assert len(bus.published) == 2


def test_unit_of_work_abstract() -> None:
    with pytest.raises(TypeError):
        UnitOfWork()  # type: ignore[abstract]


def test_unit_of_work_commit() -> None:
    uow = SpyUnitOfWork()
    uow.commit()
    assert uow.committed


def test_unit_of_work_rollback() -> None:
    uow = SpyUnitOfWork()
    uow.rollback()
    assert uow.rolled_back


def test_unit_of_work_flush() -> None:
    uow = SpyUnitOfWork()
    uow.flush()
    assert uow.flushed