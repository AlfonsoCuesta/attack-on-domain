"""Smoke tests for the supported public import surface (`deedee` package)."""

import deedee
from deedee._internal.core.event_emitter import Event


def test_deedee_exports_documented_api() -> None:
    assert deedee.__all__ == [
        "BoundedContext",
        "DomainEvent",
        "DomainException",
        "Entity",
        "RootEntity",
        "ValueObject",
    ]
    assert deedee.DomainEvent is Event
    assert issubclass(deedee.DomainException, Exception)
    assert deedee.Entity.__name__ == "Entity"
    assert deedee.RootEntity.__name__ == "RootEntity"
    assert deedee.ValueObject.__name__ == "ValueObject"
    assert deedee.BoundedContext.__name__ == "BoundedContext"
