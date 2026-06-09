from __future__ import annotations

from functools import partial
from typing import Any

from aod._internal.application.use_case import AsyncUseCase, UseCase
from aod._internal.infrastructure.container import AdapterContainer


def inject_adapters(
    container: AdapterContainer,
    use_case_cls: type[UseCase | AsyncUseCase],
    **overrides: Any,
) -> partial[UseCase | AsyncUseCase]:
    if overrides:
        container = container.with_(**overrides)

    kwargs: dict[str, Any] = {"uow": container.uow}
    if container.logger is not None:
        kwargs["logger"] = container.logger
    if container.event_bus is not None:
        kwargs["event_bus"] = container.event_bus
    if container.cache is not None:
        kwargs["cache"] = container.cache

    return partial(use_case_cls, **kwargs)