class InfrastructureException(Exception):
    """Base for errors raised by the infrastructure layer."""


class HandlerModelError(InfrastructureException):
    """A handler class is missing a required field."""

    def __init__(self, handler: type, field: str) -> None:
        super().__init__(f"Handler {handler.__name__} is missing required field '{field}'")


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


class PortNotFoundError(InfrastructureException):
    """No port with the requested name is registered on the container."""

    def __init__(self, name: str) -> None:
        super().__init__(f"No port named '{name}' registered")


class SessionNotFoundError(InfrastructureException):
    """No session of the requested type is registered on the container."""

    def __init__(self, session: type) -> None:
        super().__init__(f"No session of type {session.__name__} registered")


class AbstractSessionTypeError(InfrastructureException):
    """A handler or projection field uses abstract Session/AsyncSession directly."""

    def __init__(self, owner: str, field: str, session_type: str | type) -> None:
        name = session_type if isinstance(session_type, str) else session_type.__name__
        super().__init__(
            f"'{owner}.{field}' uses abstract {name}; use a concrete implementation instead"
        )
