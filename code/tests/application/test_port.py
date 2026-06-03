from __future__ import annotations

from abc import abstractmethod

import pytest
from aod.application import Port, UseCase
from aod._internal.core.domain_exception import MutationForbiddenException


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
        RestClientExample()  # type: ignore[abstract]


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
