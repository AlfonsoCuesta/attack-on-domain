class ApplicationException(Exception):
    """Base for errors raised by the application layer."""


class ProjectionStoreNotConfiguredError(ApplicationException):
    """No ProjectionStore was provided when one was required."""

    def __init__(self) -> None:
        super().__init__("No ProjectionStore configured")


class UnresolvableEntityError(ApplicationException):
    """Cannot determine the RootEntity type from a Command or Query."""

    def __init__(self, kind: str, item_name: str) -> None:
        super().__init__(f"Cannot determine entity for {kind} {item_name}")


class RepositoryNotRegisteredError(ApplicationException):
    """No repository is registered for the given RootEntity."""

    def __init__(self, entity_name: str) -> None:
        super().__init__(f"No repository registered for entity {entity_name}")
