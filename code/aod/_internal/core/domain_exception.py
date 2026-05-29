class DomainException(Exception):
    """Base for errors raised by domain rules and related guards."""

    pass


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
