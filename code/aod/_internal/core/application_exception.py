class ApplicationException(Exception):
    """Base for errors raised by the application layer."""


class UnresolvableEntityError(ApplicationException):
    """Cannot determine the RootEntity type from a Command or Query."""

    def __init__(self, kind: str, item_name: str) -> None:
        super().__init__(f"Cannot determine entity for {kind} {item_name}")


class CommitOutsideUnitOfWorkError(ApplicationException):
    """Commit attempted outside a UnitOfWork context."""

    def __init__(self) -> None:
        super().__init__("Cannot commit outside a UnitOfWork context")


class InvalidUseCasePortFieldError(ApplicationException):
    def __init__(self, field_name: str, cls_name: str, got: str) -> None:
        super().__init__(f"Field '{field_name}' on {cls_name} must be a Port subclass (got {got})")


class InvalidHandlerPortFieldError(ApplicationException):
    def __init__(self, field_name: str, cls_name: str) -> None:
        super().__init__(
            f"Field '{field_name}' on {cls_name} is a HandlerProtocol port missing its "
            f"generic type argument (e.g., CommandPort[PlaceOrder])"
        )
