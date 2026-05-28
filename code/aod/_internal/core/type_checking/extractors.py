from typing import Annotated, get_args, get_origin

from pydantic import BaseModel


def extract_types_from_annotation(annotation: object) -> list[type]:
    if isinstance(annotation, str):
        return []

    origin = get_origin(annotation)
    if origin is Annotated:
        return extract_types_from_annotation(get_args(annotation)[0])

    if origin is not None:
        result: list[type] = []
        for arg in get_args(annotation):
            if arg is not type(None):
                result.extend(extract_types_from_annotation(arg))
        return result

    if isinstance(annotation, type):
        return [annotation]

    return []


def get_validation_model(cls: type) -> type[BaseModel]:
    return cls.__validation_model__  # type: ignore[attr-defined]


def extract_domain_types_from_model(
    model: type[BaseModel], *domain_bases: type
) -> list[type]:
    found: list[type] = []
    for field_info in model.model_fields.values():
        if field_info.annotation is None:
            continue
        for t in extract_types_from_annotation(field_info.annotation):
            if isinstance(t, type) and any(
                issubclass(t, base) for base in domain_bases
            ):
                found.append(t)
    return found
