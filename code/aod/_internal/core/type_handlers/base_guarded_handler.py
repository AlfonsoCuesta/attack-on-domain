from __future__ import annotations

import typing

from aod._internal.core.domain_exception import (
    InvalidNestedTypeError,
)
from aod._internal.core.type_checking.extractors import extract_types_from_annotation
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.value_object import ValueObject


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


def _references_base(annotation: object, *bases: type) -> bool:
    return any(
        isinstance(t, type) and any(issubclass(t, base) for base in bases)
        for t in extract_types_from_annotation(annotation)
    )


class BaseGuardedTypeHandler:
    @staticmethod
    def check_entity(entity_cls: type[Entity]) -> None:
        for field_name, field_info in entity_cls.__model_fields__.items():
            if field_name.startswith("_"):
                continue
            field_type = field_info.annotation
            if field_type is None:
                continue
            if _references_base(field_type, RootEntity):
                raise InvalidNestedTypeError(
                    entity_cls.__name__, field_name, _type_name(field_type)
                )

    @staticmethod
    def check_root_entity(entity_cls: type[Entity]) -> None:
        BaseGuardedTypeHandler.check_entity(entity_cls)

    @staticmethod
    def check_value_object(vo_cls: type[ValueObject]) -> None:
        for field_name, field_info in vo_cls.__model_fields__.items():
            if field_name.startswith("_"):
                continue
            field_type = field_info.annotation
            if field_type is None:
                continue
            if _references_base(field_type, Entity):
                raise InvalidNestedTypeError(vo_cls.__name__, field_name, _type_name(field_type))

    @staticmethod
    def discover_types(
        root_entities: list[type[RootEntity]],
    ) -> tuple[list[type[Entity]], list[type[ValueObject]]]:
        entities: set[type[Entity]] = set()
        vos: set[type[ValueObject]] = set()
        seen: set[type] = set()
        pending: list[type] = list(root_entities)

        while pending:
            cls = pending.pop()
            if cls in seen:
                continue
            seen.add(cls)

            fields = getattr(cls, "__model_fields__", None)
            if fields is None:
                continue

            for field_name, field_info in fields.items():
                if field_name.startswith("_"):
                    continue
                field_type = field_info.annotation
                if field_type is None:
                    continue
                for t in extract_types_from_annotation(field_type):
                    if not isinstance(t, type):
                        continue
                    if (
                        issubclass(t, Entity)
                        and t is not Entity
                        and t not in root_entities
                        and t not in entities
                    ):
                        entities.add(t)
                        pending.append(t)
                    if issubclass(t, ValueObject) and t is not ValueObject and t not in vos:
                        vos.add(t)
                        pending.append(t)

        return list(entities), list(vos)
