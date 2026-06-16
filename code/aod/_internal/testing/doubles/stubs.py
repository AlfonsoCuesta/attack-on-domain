from __future__ import annotations

from inspect import iscoroutine
from typing import Any, TypeVar, cast

from aod._internal.application.port import Port

TPort = TypeVar("TPort", bound=Port)


class MethodStub:
    def __init__(self) -> None:
        self._returns: list[Any] = []
        self._calls: list[list[Any]] = []
        self._always_returns: list[Any] = []

    def returns(self, *values: Any) -> None:
        self._returns.extend(values)

    def always_returns(self, value: Any) -> None:
        self._always_returns = [value]

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self._calls.append(list(args) + list(kwargs.values()))
        if self._always_returns:
            return self._always_returns.pop(0)
        if self._returns:
            return self._returns.pop(0)
        return None

    @property
    def calls(self) -> list[list[Any]]:
        return list(self._calls)

    @property
    def called(self) -> bool:
        return len(self._calls) > 0

    @property
    def call_count(self) -> int:
        return len(self._calls)


class AsyncMethodStub:
    def __init__(self) -> None:
        self._returns: list[Any] = []
        self._calls: list[list[Any]] = []
        self._always_returns: list[Any] = []

    def returns(self, *values: Any) -> None:
        self._returns.extend(values)

    def always_returns(self, value: Any) -> None:
        self._always_returns = [value]

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self._calls.append(list(args) + list(kwargs.values()))
        if self._always_returns:
            return self._always_returns.pop(0)
        if self._returns:
            return self._returns.pop(0)
        return None

    @property
    def calls(self) -> list[list[Any]]:
        return list(self._calls)

    @property
    def called(self) -> bool:
        return len(self._calls) > 0

    @property
    def call_count(self) -> int:
        return len(self._calls)


def port_stub(port_cls: type[TPort]) -> type[TPort]:
    """Create a stub version of a Port class.

    All methods are replaced with stubs that can be configured
    to return specific values.
    """
    return _make_generic_stub(port_cls)


def _make_generic_stub(port_cls: type[TPort]) -> type[TPort]:
    stubs_attr = "_stubs"

    def __getattribute__(self: Any, name: str) -> Any:
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        stubs = object.__getattribute__(self, stubs_attr)
        if name in stubs:
            return stubs[name]
        return object.__getattribute__(self, name)

    methods: dict[str, Any] = {
        stubs_attr: {},
        "__getattribute__": __getattribute__,
    }
    for name in dir(port_cls):
        if name.startswith("_"):
            continue
        attr = getattr(port_cls, name)
        if callable(attr):
            if iscoroutine(attr):
                methods[name] = MethodStub()
            else:
                methods[name] = AsyncMethodStub()
    return cast(type[TPort], type(f"Stub{port_cls.__name__}", (port_cls,), methods))
