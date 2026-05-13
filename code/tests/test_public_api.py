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
        "Field",
        "PrivateField",
        "field_validator",
        "post_init",
    ]
    assert aod.DomainEvent is Event
    assert issubclass(aod.DomainException, Exception)
    assert aod.Entity.__name__ == "Entity"
    assert aod.RootEntity.__name__ == "RootEntity"
    assert aod.ValueObject.__name__ == "ValueObject"
    assert aod.BoundedContext.__name__ == "BoundedContext"
    assert aod.Field.__name__ == "Field"
    assert aod.PrivateField.__name__ == "PrivateField"
    assert aod.field_validator.__name__ == "field_validator"
    assert aod.post_init.__name__ == "post_init"
