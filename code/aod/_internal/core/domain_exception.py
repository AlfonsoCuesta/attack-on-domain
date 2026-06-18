class DomainException(Exception):
    """Base for errors raised by domain rules and related guards."""


class MutationForbiddenException(DomainException):
    """Raised when a mutable or immutable object is updated outside allowed context."""

    def __init__(self, message: str = "Cannot mutate this object") -> None:
        super().__init__(message)


class InvalidEntityTypeError(DomainException):
    """Raised when a type registered as aggregate root is not an Entity subclass."""

    def __init__(self, type_name: str) -> None:
        super().__init__(f"{type_name} is not an Entity")


class InvalidRootEntityTypeError(DomainException):
    """Raised when a type is an Entity but not declared as aggregate root."""

    def __init__(self, type_name: str) -> None:
        super().__init__(f"{type_name} is not a root Entity")


class InvalidServiceTypeError(DomainException):
    """Raised when a type registered as service is not a Service subclass."""

    def __init__(self, type_name: str) -> None:
        super().__init__(f"{type_name} is not a Service")


class ClassExpectedError(DomainException):
    """Raised when a class was required but a non-type value was given."""

    def __init__(self, *, role: str, got: object) -> None:
        super().__init__(f"Expected a class for {role}, got {type(got).__name__} instance")


class InvalidNestedTypeError(DomainException):
    """Raised when an Entity field references a forbidden domain type."""

    def __init__(self, entity_name: str, field_name: str, type_name: str) -> None:
        super().__init__(
            f"Entity '{entity_name}' field '{field_name}' references "
            f"'{type_name}', which is not allowed"
        )


class InvalidServiceParameterError(DomainException):
    """Raised when a Service method parameter references a disallowed domain type."""

    def __init__(
        self, service_name: str, method_name: str, param_name: str, type_name: str
    ) -> None:
        super().__init__(
            f"Service '{service_name}' method '{method_name}' parameter "
            f"'{param_name}' has type '{type_name}', which is not allowed"
        )


class DuplicateDomainTypeError(DomainException):
    """Raised when a domain type is registered in more than one BoundedContext."""

    def __init__(self, type_name: str, role: str, first_context: str) -> None:
        super().__init__(
            f"{type_name} ({role}) is already registered in bounded context '{first_context}'"
        )


class InvarianceException(DomainException, ValueError):
    """Raised when a field or model invariance is violated.

    Inherits from ValueError so Pydantic catches and wraps it
    in ValidationError during normal construction flow.
    """

    def __init__(self, name: str, message: str = "") -> None:
        self.name = name
        super().__init__(message or f"Invariance '{name}' violated")


class InvalidCommandFieldTypeError(DomainException):
    """Field in a Command or Query references a non-root Entity."""

    def __init__(self, cls_name: str, field_name: str, type_name: str) -> None:
        super().__init__(
            f"Field '{field_name}' in {cls_name} references non-root Entity "
            f"type '{type_name}'. Only RootEntity is allowed in Command/Query fields."
        )


class InvalidQueryResultTypeError(DomainException):
    """Query TResult generic argument does not include a RootEntity."""

    def __init__(self, cls_name: str, result_type_name: str) -> None:
        super().__init__(
            f"Result type for {cls_name} must include a RootEntity, got {result_type_name}"
        )


class InvalidGenericTypeArgError(DomainException):
    """A generic type argument does not satisfy its constraint."""

    def __init__(self, arg_name: str, cls_name: str, expected: str, got: str) -> None:
        super().__init__(f"{arg_name} for {cls_name} must be a {expected} subclass, got {got}")


class ModelValidationError(DomainException):
    """Pydantic validation failed during model construction."""

    def __init__(self, cls_name: str, message: str) -> None:
        super().__init__(f"Validation failed for {cls_name}: {message}")


class MissingHandlerError(DomainException):
    """Raised when a module is missing a handler for a contract or port."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class MissingPortError(DomainException):
    """Raised when a module is missing an implementation for a port."""

    def __init__(self, port_name: str) -> None:
        super().__init__(f"Port {port_name} has no implementation in module")
