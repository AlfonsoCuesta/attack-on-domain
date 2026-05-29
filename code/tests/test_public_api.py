"""Smoke tests for the supported public import surface (`aod` package)."""

import aod
import aod.exceptions
import aod.validation
from aod._internal.core.event_emitter import Event


def test_aod_exports_documented_api() -> None:
    assert aod.__all__ == [
        "App",
        "BoundedContext",
        "DomainEvent",
        "Entity",
        "RootEntity",
        "Service",
        "ValueObject",
        "Field",
        "PrivateField",
    ]
    assert aod.App.__name__ == "App"
    assert aod.DomainEvent is Event
    assert aod.Entity.__name__ == "Entity"
    assert aod.RootEntity.__name__ == "RootEntity"
    assert aod.Service.__name__ == "Service"
    assert aod.ValueObject.__name__ == "ValueObject"
    assert aod.BoundedContext.__name__ == "BoundedContext"
    assert aod.Field.__name__ == "Field"
    assert aod.PrivateField.__name__ == "PrivateField"


def test_aod_exceptions_documented_api() -> None:
    assert aod.exceptions.__all__ == ["DomainException", "MutationForbiddenException"]


def test_aod_validation_documented_api() -> None:
    assert aod.validation.__all__ == [
        "AfterValidator",
        "BeforeValidator",
        "field_invariance",
        "invariance",
        "super_context",
    ]
