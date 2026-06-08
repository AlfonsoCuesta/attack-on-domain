"""Smoke tests for the supported public import surface."""

import aod.application
import aod.application.async_
import aod.application.exceptions
import aod.domain
import aod.domain.exceptions
import aod.domain.validation
import aod.events
import aod.exceptions
import aod.infrastructure
import aod.infrastructure.async_
import aod.infrastructure.exceptions
from aod._internal.core.event_emitter import Event


def test_aod_domain_exports_documented_api() -> None:
    assert aod.domain.__all__ == [
        "App",
        "BoundedContext",
        "DomainException",
        "Entity",
        "RootEntity",
        "Service",
        "ValueObject",
        "Field",
        "PrivateField",
    ]
    assert aod.domain.App.__name__ == "App"
    assert aod.domain.DomainException.__name__ == "DomainException"
    assert aod.domain.Entity.__name__ == "Entity"
    assert aod.domain.RootEntity.__name__ == "RootEntity"
    assert aod.domain.Service.__name__ == "Service"
    assert aod.domain.ValueObject.__name__ == "ValueObject"
    assert aod.domain.BoundedContext.__name__ == "BoundedContext"
    assert aod.domain.Field.__name__ == "Field"
    assert aod.domain.PrivateField.__name__ == "PrivateField"


def test_aod_domain_exceptions_documented_api() -> None:
    assert aod.domain.exceptions.__all__ == [
        "ClassExpectedError",
        "DuplicateDomainTypeError",
        "HandlerEntityMismatchError",
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
        "UnresolvableHandlerTypeError",
    ]


def test_aod_application_exports_documented_api() -> None:
    assert aod.application.__all__ == [
        "ApplicationException",
        "Cache",
        "Command",
        "EventBus",
        "Logger",
        "Port",
        "ProjectionCommand",
        "ProjectionQuery",
        "Query",
        "ReadModel",
        "UnitOfWork",
        "UseCase",
    ]
    assert aod.application.ApplicationException.__name__ == "ApplicationException"
    assert aod.application.Cache.__name__ == "Cache"
    import inspect
    assert inspect.iscoroutinefunction(aod.application.async_.Cache.get)

    assert aod.application.async_.__all__ == [
        "Cache",
        "EventBus",
        "Logger",
        "UnitOfWork",
        "UseCase",
    ]


def test_aod_application_exceptions_documented_api() -> None:
    assert aod.application.exceptions.__all__ == [
        "ProjectionStoreNotConfiguredError",
        "RepositoryNotRegisteredError",
        "UnresolvableEntityError",
    ]


def test_aod_infrastructure_exports_documented_api() -> None:
    assert aod.infrastructure.__all__ == [
        "CommandHandler",
        "InfrastructureException",
        "ProjectionCommandHandler",
        "ProjectionQueryHandler",
        "ProjectionStore",
        "PromisedCache",
        "QueryHandler",
        "Repository",
    ]
    assert aod.infrastructure.InfrastructureException.__name__ == "InfrastructureException"

    assert aod.infrastructure.async_.__all__ == [
        "CommandHandler",
        "PromisedCache",
        "ProjectionCommandHandler",
        "ProjectionQueryHandler",
        "ProjectionStore",
        "QueryHandler",
        "Repository",
    ]


def test_aod_infrastructure_exceptions_documented_api() -> None:
    assert aod.infrastructure.exceptions.__all__ == [
        "DuplicateHandlerError",
        "DuplicateProjectionHandlerError",
        "HandlerNotFoundError",
        "HandlerResultTypeError",
        "ProjectionHandlerNotFoundError",
        "UnresolvableProjectionTypeError",
    ]


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
        "InfrastructureException",
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


def test_aod_events_documented_api() -> None:
    assert aod.events.__all__ == [
        "Event",
        "EventCollector",
    ]
    assert aod.events.Event is Event
    assert aod.events.EventCollector.__name__ == "EventCollector"


def test_aod_domain_validation_documented_api() -> None:
    assert aod.domain.validation.__all__ == [
        "AfterValidator",
        "BeforeValidator",
        "field_invariance",
        "invariance",
        "inherit_context",
    ]
