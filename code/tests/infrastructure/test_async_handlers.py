from __future__ import annotations

import pytest
from aod._internal.domain.entity import RootEntity
from aod.application import Command, Query
from aod.infrastructure.async_ import CommandHandler, QueryHandler


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
