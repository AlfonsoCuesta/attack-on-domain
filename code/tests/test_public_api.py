"""Smoke tests for the supported public import surface."""

import aod.domain
import aod.domain.validation
import aod.exceptions
from aod._internal.core.event_emitter import Event


def test_aod_domain_exports_documented_api() -> None:
    assert aod.domain.__all__ == [
        "App",
        "BoundedContext",
        "DomainEvent",
        "EventCollector",
        "Entity",
        "RootEntity",
        "Service",
        "ValueObject",
        "Field",
        "PrivateField",
    ]
    assert aod.domain.App.__name__ == "App"
    assert aod.domain.DomainEvent is Event
    assert aod.domain.Entity.__name__ == "Entity"
    assert aod.domain.RootEntity.__name__ == "RootEntity"
    assert aod.domain.Service.__name__ == "Service"
    assert aod.domain.ValueObject.__name__ == "ValueObject"
    assert aod.domain.BoundedContext.__name__ == "BoundedContext"
    assert aod.domain.Field.__name__ == "Field"
    assert aod.domain.PrivateField.__name__ == "PrivateField"
    assert aod.domain.EventCollector.__name__ == "EventCollector"


def test_aod_exceptions_documented_api() -> None:
    assert aod.exceptions.__all__ == [
        "ApplicationException",
        "ClassExpectedError",
        "DomainException",
        "DuplicateDomainTypeError",
        "DuplicateHandlerError",
        "DuplicateProjectionHandlerError",
        "HandlerEntityMismatchError",
        "HandlerNotFoundError",
        "HandlerResultTypeError",
        "HandlerTypeMismatchError",
        "InvalidCommandFieldTypeError",
        "InvalidEntityTypeError",
        "InvalidGenericTypeArgError",
        "InvalidNestedTypeError",
        "InvalidProjectionTypeError",
        "InvalidQueryResultTypeError",
        "InvalidRootEntityTypeError",
        "InvalidServiceParameterError",
        "InvalidServiceTypeError",
        "InvarianceException",
        "MutationForbiddenException",
        "ProjectionHandlerNotFoundError",
        "ProjectionStoreNotConfiguredError",
        "RepositoryNotRegisteredError",
        "UnresolvableEntityError",
        "UnresolvableHandlerTypeError",
        "UnresolvableProjectionTypeError",
    ]


def test_aod_domain_validation_documented_api() -> None:
    assert aod.domain.validation.__all__ == [
        "AfterValidator",
        "BeforeValidator",
        "field_invariance",
        "invariance",
        "inherit_context",
    ]
