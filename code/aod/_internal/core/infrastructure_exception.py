class InfrastructureException(Exception):
    """Base for errors raised by the infrastructure layer."""


class UnresolvableProjectionTypeError(InfrastructureException):
    """Cannot determine the projection type from a handler's generic bases."""

    def __init__(self, handler_name: str) -> None:
        super().__init__(f"Cannot determine projection type for {handler_name}")


class DuplicateProjectionHandlerError(InfrastructureException):
    """A second handler was registered for the same projection type."""

    def __init__(self, type_name: str) -> None:
        super().__init__(f"Duplicate handler for {type_name}")


class ProjectionHandlerNotFoundError(InfrastructureException):
    """No handler is registered for the given projection type."""

    def __init__(self, name: str) -> None:
        super().__init__(f"No handler registered for {name}")


class DuplicateHandlerError(InfrastructureException):
    """A second handler was registered for the same Command or Query type."""

    def __init__(self, type_name: str) -> None:
        super().__init__(f"Duplicate handler for {type_name}")


class HandlerNotFoundError(InfrastructureException):
    """No handler is registered for the given Command or Query type."""

    def __init__(self, kind: str, name: str) -> None:
        super().__init__(f"No {kind} handler registered for {name}")


class HandlerResultTypeError(InfrastructureException):
    """Handler.handle() returned an object of the wrong type."""

    def __init__(self, handler_name: str, got: str, expected: str) -> None:
        super().__init__(f"{handler_name}.handle() returned {got}, expected {expected}")
