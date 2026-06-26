from __future__ import annotations

from aod._internal.application.contracts.contracts import (
    _validate_fields_no_entity,
    _validate_result_contains_root_entity,
)
from aod._internal.domain.entity import RootEntity
from aod._internal.domain.entity_id import EntityId


class IntId(EntityId):
    value: int


class User(RootEntity):
    id: IntId
    name: str


def test_validate_fields_no_entity_skips_when_no_own_fields() -> None:
    class NoFields:
        pass

    _validate_fields_no_entity(NoFields)


def test_validate_fields_no_entity_handles_name_error() -> None:
    class ForwardRefFields:
        a: "NonExistentType"  # noqa: F821 # type: ignore

    _validate_fields_no_entity(ForwardRefFields)


def test_validate_result_contains_root_entity_returns_when_result_type_none() -> None:
    class NoResultType:
        pass

    _validate_result_contains_root_entity(NoResultType, type("QueryType", (), {}))
