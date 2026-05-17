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
        super().__init__(
            f"Expected a class for {role}, got {type(got).__name__} instance"
        )
