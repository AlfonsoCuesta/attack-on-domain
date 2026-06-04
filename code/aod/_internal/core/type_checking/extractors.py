from typing import Annotated, get_args, get_origin


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
