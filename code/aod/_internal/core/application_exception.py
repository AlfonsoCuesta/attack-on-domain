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