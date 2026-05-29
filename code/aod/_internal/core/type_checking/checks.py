import inspect
import typing

from aod._internal.core.domain_exception import (
    InvalidNestedTypeError,
    InvalidServiceParameterError,
)

from .extractors import extract_types_from_annotation


def _type_name(annotation: object) -> str:
    origin = typing.get_origin(annotation)
    if origin is not None:
        args = typing.get_args(annotation)
        filtered = [a for a in args if a is not type(None)]
        if origin is typing.Union and len(filtered) == 1:
            return _type_name(filtered[0])
        items = ", ".join(_type_name(a) for a in filtered)
        return f"{_type_name(origin)}[{items}]"
    if isinstance(annotation, type):
        return annotation.__name__
    return str(annotation)


def _resolve_annotation(annotation: object, cls: type) -> object:
    if isinstance(annotation, str):
        try:
            return typing.get_type_hints(cls).get("_dummy", annotation)
        except Exception:
            return None
    return annotation


def check_entity(entity_cls: type) -> None:
    try:
        hints = typing.get_type_hints(entity_cls)
    except Exception:
        return

    for field_name, field_type in hints.items():
        if field_name.startswith("_"):
            continue
        if _references_base(field_type, _get_root_entity_type(entity_cls)):
            raise InvalidNestedTypeError(entity_cls.__name__, field_name, _type_name(field_type))


def check_root_entity(entity_cls: type) -> None:
    check_entity(entity_cls)


def _get_root_entity_type(entity_cls: type) -> type:
    from aod._internal.domain.entity import RootEntity

    return RootEntity


def _references_base(annotation: object, *bases: type) -> bool:
    return any(
        isinstance(t, type) and any(issubclass(t, base) for base in bases)
        for t in extract_types_from_annotation(annotation)
    )


def check_value_object(vo_cls: type) -> None:
    from aod._internal.domain.entity import Entity

    try:
        hints = typing.get_type_hints(vo_cls)
    except Exception:
        return

    for field_name, field_type in hints.items():
        if field_name.startswith("_"):
            continue
        if _references_base(field_type, Entity):
            raise InvalidNestedTypeError(vo_cls.__name__, field_name, _type_name(field_type))


def check_service(service_cls: type) -> None:
    from aod._internal.domain.entity import Entity, RootEntity

    for method_name, method in inspect.getmembers(service_cls, inspect.isfunction):
        if method_name.startswith("_"):
            continue
        try:
            sig = inspect.signature(method)
        except (ValueError, TypeError):  # fmt: skip
            continue

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
                    _type_name(resolved),
                )

        if sig.return_annotation is not inspect.Parameter.empty:
            resolved = _resolve_annotation(sig.return_annotation, service_cls)
            if resolved is not None and _is_entity_param(resolved, Entity, RootEntity):
                raise InvalidServiceParameterError(
                    service_cls.__name__,
                    method_name,
                    "return",
                    _type_name(resolved),
                )


def _is_entity_param(annotation: object, entity: type, root_entity: type) -> bool:
    for t in extract_types_from_annotation(annotation):
        if isinstance(t, type):
            if issubclass(t, root_entity):
                continue
            if issubclass(t, entity):
                return True
    return False
