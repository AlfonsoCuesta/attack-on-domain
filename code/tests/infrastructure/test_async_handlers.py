from __future__ import annotations

import pytest
from aod._internal.core.domain_exception import DomainException
from aod._internal.domain.entity import RootEntity
from aod.application import Command, Query
from aod.infrastructure.handlers.async_ import CommandHandler, QueryHandler


class User(RootEntity):
    id: int
    name: str


class CreateUser(Command[User, User]):
    name: str


class GetUser(Query[User, User | None]):
    user_id: int


class CreateUserHandler(CommandHandler[CreateUser]):
    async def handle(self, cmd: CreateUser) -> User:
        return User(id=1, name=cmd.name)


class GetUserHandler(QueryHandler[GetUser]):
    async def handle(self, query: GetUser) -> User | None:
        if query.user_id == 1:
            return User(id=1, name="Alice")
        return None


async def test_is_abstract() -> None:
    with pytest.raises(TypeError):
        CommandHandler[CreateUser]()


async def test_without_handle_is_abstract() -> None:
    class Incomplete(CommandHandler[CreateUser]):
        pass

    with pytest.raises(TypeError):
        Incomplete()


async def test_concrete_handler_works() -> None:
    h = CreateUserHandler()
    cmd = CreateUser(name="Alice")
    result = await h.handle(cmd)
    assert isinstance(result, User)
    assert result.name == "Alice"


async def test_query_handler_works() -> None:
    h = GetUserHandler()
    result = await h.handle(GetUser(user_id=1))
    assert result is not None
    assert result.name == "Alice"


async def test_query_handler_returns_none() -> None:
    h = GetUserHandler()
    result = await h.handle(GetUser(user_id=999))
    assert result is None


async def test_invalid_generic_raises() -> None:
    with pytest.raises(DomainException, match="Generic parameter for"):

        class _(CommandHandler[str]):  # type: ignore
            async def handle(self, cmd: str) -> str:
                return cmd


async def test_query_invalid_generic_raises() -> None:
    with pytest.raises(DomainException, match="Generic parameter for"):

        class _(QueryHandler[int]):  # type: ignore
            async def handle(self, query: int) -> int:
                return query
