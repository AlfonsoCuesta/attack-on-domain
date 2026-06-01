from __future__ import annotations

import inspect
import typing
from functools import lru_cache

from aod._internal.core.domain_exception import InvalidServiceParameterError
from aod._internal.core.fields import is_public_field
from aod._internal.core.type_checking.extractors import extract_types_from_annotation
from aod._internal.core.type_utils import type_name
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.service import Service


@lru_cache(maxsize=None)
def _resolved_hints(cls: type) -> dict[str, object]:
    try:
        return typing.get_type_hints(cls)
    except Exception:
        return {}


def _resolve_annotation(annotation: object, cls: type) -> object:
    if isinstance(annotation, str):
        return _resolved_hints(cls).get(annotation, annotation)
    return annotation


def _is_entity_param(
    annotation: object, entity: type[Entity], root_entity: type[RootEntity]
) -> bool:
    for t in extract_types_from_annotation(annotation):
        if isinstance(t, type):
            if issubclass(t, root_entity):
                continue
            if issubclass(t, entity):
                return True
    return False


class ServiceTypeHandler:
    @staticmethod
    def check_service(service_cls: type[Service]) -> None:
        for method_name, method in inspect.getmembers(service_cls, inspect.isfunction):
            if not is_public_field(method_name):
                continue
            # fmt: off
            try:
                sig = inspect.signature(method)
            except (ValueError, TypeError):
                continue
            # fmt: on

            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue
                if param.annotation is inspect.Parameter.empty:
                    continue
                resolved = _resolve_annotation(param.annotation, service_cls)
                if resolved is not None and _is_entity_param(resolved, Entity, RootEntity):
                    raise InvalidServiceParameterError(
                        service_cls.__name__,
                        method_name,
                        param_name,
                        type_name(resolved),
                    )

            if sig.return_annotation is not inspect.Parameter.empty:
                resolved = _resolve_annotation(sig.return_annotation, service_cls)
                if resolved is not None and _is_entity_param(resolved, Entity, RootEntity):
                    raise InvalidServiceParameterError(
                        service_cls.__name__,
                        method_name,
                        "return",
                        type_name(resolved),
                    )
