from __future__ import annotations

from abc import abstractmethod
from typing import Any, TypeVar, cast

from aod._internal.application.port import Port
from aod._internal.application.repository import Command, Query, Repository
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases
from aod._internal.domain.entity import RootEntity
from aod._internal.type_checks.contract_checks import extract_root_entity

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")


class _UnitOfWorkBase(Port):
    repositories: list[Repository[Any, Any]] = Field(default_factory=list)
    is_dirty: bool = Field(default=False, init=False)
    _repo_map: dict[type[RootEntity], Repository[Any, Any]] = PrivateField(default_factory=dict)

    def __post_init__(self) -> None:
        for repo in self.repositories:
            entity = extract_root_entity(repo)
            if entity is not None and issubclass(entity, RootEntity):
                self._repo_map[entity] = repo

    def _resolve_repo(self, item: Command | Query) -> Repository[Any, Any]:
        base_type = Command if isinstance(item, Command) else Query
        kind = "command" if isinstance(item, Command) else "query"
        entity = get_generic_arg_from_orig_bases(type(item), base_type)
        if not isinstance(entity, type) or not issubclass(entity, RootEntity):
            msg = f"Cannot determine entity for {kind} {type(item).__name__}"
            raise DomainException(msg)
        repo = self._repo_map.get(entity)
        if repo is None:
            msg = f"No repository registered for entity {entity.__name__}"
            raise DomainException(msg)
        return repo


class UnitOfWork(_UnitOfWorkBase):
    def command(self, cmd: Command[TEntity, TResult]) -> TResult:
        result = cast(TResult, self._resolve_repo(cmd).command(cmd))
        self.is_dirty = True
        return result

    def query(self, query: Query[TEntity, TResult]) -> TResult:
        return cast(TResult, self._resolve_repo(query).query(query))

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...
