from __future__ import annotations

from typing import Any, TypeVar, cast

from aod._internal.application.handler import (
    AsyncCommandPort,
    AsyncQueryPort,
    CommandPort,
    QueryPort,
)
from aod._internal.testing.doubles.stubs import _make_callable_stub

TContract = TypeVar("TContract", bound=CommandPort | QueryPort | AsyncCommandPort | AsyncQueryPort)


def _make_handler_spy(
    port_protocol: type[TContract],
    *,
    returns: Any = None,
    raises: Exception | None = None,
) -> TContract:
    handle_stub = _make_callable_stub(port_protocol.handle)
    if raises is not None:
        handle_stub.side_effect = raises
    elif returns is not None:
        handle_stub.return_value = returns
    else:
        handle_stub.return_value = None
    stubs: dict[str, Any] = {
        "handle": handle_stub,
        "__skip_method_wrapping__": True,
    }
    spy_cls = cast(
        type[TContract],
        type(
            f"Spy{port_protocol.__name__}",
            (port_protocol,),
            stubs,
        ),
    )
    if getattr(spy_cls, "handle") is not handle_stub:
        setattr(spy_cls, "handle", handle_stub)
    return spy_cls()


def spy_command_handler(
    *,
    returns: Any = None,
    raises: Exception | None = None,
) -> Any:
    return _make_handler_spy(CommandPort, returns=returns, raises=raises)


def spy_query_handler(
    *,
    returns: Any = None,
    raises: Exception | None = None,
) -> Any:
    return _make_handler_spy(QueryPort, returns=returns, raises=raises)


def spy_async_command_handler(
    *,
    returns: Any = None,
    raises: Exception | None = None,
) -> Any:
    return _make_handler_spy(AsyncCommandPort, returns=returns, raises=raises)


def spy_async_query_handler(
    *,
    returns: Any = None,
    raises: Exception | None = None,
) -> Any:
    return _make_handler_spy(AsyncQueryPort, returns=returns, raises=raises)
