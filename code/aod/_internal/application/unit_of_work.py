from __future__ import annotations

from abc import abstractmethod
from typing import TypeVar, cast

from aod._internal.application.port import Port
from aod._internal.application.repository import Command, Query, Repository
from aod._internal.core.domain_exception import DomainException
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases
from aod._internal.domain.entity import RootEntity
from aod._internal.type_checks.contract_checks import extract_root_entity

TEntity = TypeVar("TEntity")
TResult = TypeVar("TResult")


class UnitOfWork(Port):
    repositories: list[Repository] = Field(default_factory=list)
    _repo_map: dict[type[RootEntity], Repository] = PrivateField(default_factory=dict)

    def __post_init__(self) -> None:
        for repo in self.repositories:
            entity = extract_root_entity(repo)
            if entity is not None and issubclass(entity, RootEntity):
                self._repo_map[entity] = repo

    def command(self, cmd: Command[TEntity, TResult]) -> TResult:
        entity = get_generic_arg_from_orig_bases(type(cmd), Command)
        if not isinstance(entity, type) or not issubclass(entity, RootEntity):
            msg = f"Cannot determine entity for command {type(cmd).__name__}"
            raise DomainException(msg)

        repo = self._repo_map.get(entity)
        if repo is None:
            msg = f"No repository registered for entity {entity.__name__}"
            raise DomainException(msg)

        return cast(TResult, repo.command(cmd))

    def query(self, query: Query[TEntity, TResult]) -> TResult:
        entity = get_generic_arg_from_orig_bases(type(query), Query)
        if not isinstance(entity, type) or not issubclass(entity, RootEntity):
            msg = f"Cannot determine entity for query {type(query).__name__}"
            raise DomainException(msg)

        repo = self._repo_map.get(entity)
        if repo is None:
            msg = f"No repository registered for entity {entity.__name__}"
            raise DomainException(msg)

        return cast(TResult, repo.query(query))

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...
