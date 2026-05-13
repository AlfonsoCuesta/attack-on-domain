"""Smoke tests for the supported public import surface (`aod` package)."""

import aod
from aod._internal.core.event_emitter import Event


def test_aod_exports_documented_api() -> None:
    assert aod.__all__ == [
        "BoundedContext",
        "DomainEvent",
        "DomainException",
        "Entity",
        "RootEntity",
        "ValueObject",
    ]
    assert aod.DomainEvent is Event
    assert issubclass(aod.DomainException, Exception)
    assert aod.Entity.__name__ == "Entity"
    assert aod.RootEntity.__name__ == "RootEntity"
    assert aod.ValueObject.__name__ == "ValueObject"
    assert aod.BoundedContext.__name__ == "BoundedContext"
