from __future__ import annotations

from typing import Any, TypeVar

from aod._internal.core.base_validator import _use_raw_model
from aod._internal.core.base_guarded import BaseGuarded
from aod._internal.core.event_emitter import Event
from aod._internal.core.invariances.invariances import is_validator

T = TypeVar("T")

__all__ = [
    "build",
    "events_of",
    "assert_event_emitted",
    "assert_no_events",
    "check_invariant",
]


def build(cls: type[T], **kwargs: Any) -> T:
    token = _use_raw_model.set(True)
    try:
        return cls(**kwargs)
    finally:
        _use_raw_model.reset(token)


def events_of(obj: BaseGuarded) -> list[Event]:
    return list(obj._event_emitter.poll_events())


def assert_event_emitted(events: list[Event], event_type: type[Event], **attrs: Any) -> Event:
    for e in events:
        if isinstance(e, event_type) and all(getattr(e, k) == v for k, v in attrs.items()):
            return e
    msg = f"Expected {event_type.__name__}({attrs}) to be emitted"
    raise AssertionError(msg)


def assert_no_events(events: list[Event]) -> None:
    if events:
        raise AssertionError(f"Expected no events, got {len(events)}")


def check_invariant(cls: type, name: str, **data: Any) -> None:
    registry: dict[str, Any] = getattr(cls, "__validator_registry__", {})
    validator_fn = registry.get(name)
    if validator_fn is None:
        names = ", ".join(sorted(registry))
        msg = f"No invariant named {name!r} on {cls.__name__}. Available: {names}"
        raise ValueError(msg)

    info = is_validator(validator_fn)
    if info is None and isinstance(validator_fn, classmethod):
        info = is_validator(validator_fn.__func__)

    obj = build(cls, **data)

    if info and info.args:
        field = info.args[0]
        value = getattr(obj, field)
        if isinstance(validator_fn, classmethod):
            validator_fn.__func__(cls, value)
        else:
            validator_fn(cls, value)
    else:
        if isinstance(validator_fn, classmethod):
            validator_fn.__func__(obj)
        else:
            validator_fn(obj)
