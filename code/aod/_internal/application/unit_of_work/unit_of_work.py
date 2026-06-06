from __future__ import annotations

from abc import abstractmethod
from typing import Any, TypeVar

from aod._internal.application.port import Port
from aod._internal.application.projection import ProjectionCommand, ProjectionQuery, ReadModel
from aod._internal.application.projection.projection_store import ProjectionStore
from aod._internal.application.repository import Command, Query, Repository
from aod._internal.core.domain_exception import ApplicationException
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases
from aod._internal.domain.entity import RootEntity
from aod._internal.type_checks.contract_checks import extract_root_entity

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")
T = TypeVar("T", bound=ReadModel | None)


class _NullProjectionStore:
    def query(self, query: ProjectionQuery[T]) -> T:
        msg = "No ProjectionStore configured"
        raise ApplicationException(msg)

    def command(self, command: ProjectionCommand[T]) -> T:
        msg = "No ProjectionStore configured"
        raise ApplicationException(msg)


class _UnitOfWorkBase(Port):
    repositories: list[Repository[Any, Any]] = Field(default_factory=list)
    projection_store: ProjectionStore = Field(default_factory=_NullProjectionStore)
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
            raise ApplicationException(msg)
        repo = self._repo_map.get(entity)
        if repo is None:
            msg = f"No repository registered for entity {entity.__name__}"
            raise ApplicationException(msg)
        return repo

    def command(self, command: Command | ProjectionCommand[T]) -> object:
        if isinstance(command, ProjectionCommand):
            return self.projection_store.command(command)
        result = self._resolve_repo(command).command(command)
        self.is_dirty = True
        return result

    def query(self, query: Query | ProjectionQuery) -> object:
        if isinstance(query, ProjectionQuery):
            return self.projection_store.query(query)
        return self._resolve_repo(query).query(query)


class UnitOfWork(_UnitOfWorkBase):
    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...
