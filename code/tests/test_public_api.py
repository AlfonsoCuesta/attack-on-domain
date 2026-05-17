"""Smoke tests for the supported public import surface (`aod` package)."""

import aod
import aod.exceptions
import aod.validation
from aod._internal.core.event_emitter import Event


def test_aod_exports_documented_api() -> None:
    assert aod.__all__ == [
        "BoundedContext",
        "DomainEvent",
        "Entity",
        "RootEntity",
        "ValueObject",
        "Field",
        "PrivateField",
    ]
    assert aod.DomainEvent is Event
    assert aod.Entity.__name__ == "Entity"
    assert aod.RootEntity.__name__ == "RootEntity"
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
        "field_validator",
        "post_init",
        "post_init_validation",
    ]
