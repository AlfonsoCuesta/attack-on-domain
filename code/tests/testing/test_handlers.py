from __future__ import annotations

import pytest
from aod._internal.core.domain_exception import (
    DomainException,
    MutationForbiddenException,
)
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.entity_id import EntityId
from aod.application import Command, Query
from aod.infrastructure import CommandHandler, QueryHandler


class IntId(EntityId):
    value: int


class User(RootEntity):
    id: IntId
    name: str
    email: str


class Order(RootEntity):
    id: IntId
    total: float


class CreateUser(Command[User, User]):
    name: str
    email: str


class GetUser(Query[User, User | None]):
    user_id: int


class DeleteUser(Command[User, None]):
    user_id: int


class CountUsers(Query[User, tuple[int, User]]):
    pass


class CreateOrder(Command[Order, Order]):
    total: float


class CreateUserHandler(CommandHandler[CreateUser]):
    def handle(self, command: CreateUser) -> User:
        return User(id=IntId(value=1), name=command.name, email=command.email)


class GetUserHandler(QueryHandler[GetUser]):
    def handle(self, query: GetUser) -> User | None:
        if query.user_id == 1:
            return User(id=IntId(value=1), name="Alice", email="a@b.com")
        return None


class DeleteUserHandler(CommandHandler[DeleteUser]):
    def handle(self, command: DeleteUser) -> None: ...


class CountUsersHandler(QueryHandler[CountUsers]):
    def handle(self, query: CountUsers) -> tuple[int, User]:
        return (42, User(id=IntId(value=1), name="dummy", email="d@d.com"))


class CreateOrderHandler(CommandHandler[CreateOrder]):
    def handle(self, command: CreateOrder) -> Order:
        return Order(id=IntId(value=1), total=command.total)


class BaseCommandHandler(CommandHandler[CreateUser]):
    def handle(self, command: CreateUser) -> User:
        return User(id=IntId(value=99), name=command.name, email=command.email)


class TestCommand:
    def test_can_be_instantiated(self) -> None:
        cmd = CreateUser(name="Alice", email="a@b.com")
        assert cmd.name == "Alice"
        assert cmd.email == "a@b.com"

    def test_is_data_only(self) -> None:
        cmd = CreateUser(name="Alice", email="a@b.com")
        assert not hasattr(type(cmd), "execute")

    def test_is_immutable(self) -> None:
        cmd = CreateUser(name="Alice", email="a@b.com")
        with pytest.raises(MutationForbiddenException):
            cmd.name = "Bob"

    def test_fields_can_be_read(self) -> None:
        cmd = CreateUser(name="Alice", email="a@b.com")
        assert cmd.name == "Alice"

    def test_default_values(self) -> None:
        cmd = CountUsers()
        assert isinstance(cmd, Query)

    def test_repr(self) -> None:
        cmd = CreateUser(name="Alice", email="a@b.com")
        rep = repr(cmd)
        assert "CreateUser" in rep
        assert "Alice" in rep

    def test_different_entity_types(self) -> None:
        cmd = CreateOrder(total=99.99)
        assert cmd.total == 99.99

    def test_with_result_none(self) -> None:
        cmd = DeleteUser(user_id=5)
        assert cmd.user_id == 5

    def test_invalid_entity_raises(self) -> None:
        with pytest.raises(DomainException, match="TEntity for"):

            class _(Command[str, int]):
                pass

    def test_non_root_entity_field_raises(self) -> None:
        with pytest.raises(DomainException, match="non-root Entity"):

            class _(Command[User, User]):
                items: list[Entity]

    def test_nested_entity_field_raises(self) -> None:
        with pytest.raises(DomainException, match="non-root Entity"):

            class _(Command[User, User]):
                items: list[tuple[int, Entity | None]]

    def test_root_entity_field_allowed(self) -> None:
        class _(Command[User, User]):
            user: User

    def test_nested_root_entity_allowed(self) -> None:
        class _(Command[User, User]):
            items: list[tuple[int, User]]


class TestQuery:
    def test_can_be_instantiated(self) -> None:
        q = GetUser(user_id=1)
        assert q.user_id == 1

    def test_is_immutable(self) -> None:
        q = GetUser(user_id=1)
        with pytest.raises(MutationForbiddenException):
            q.user_id = 99

    def test_repr(self) -> None:
        q = GetUser(user_id=1)
        rep = repr(q)
        assert "GetUser" in rep
        assert "user_id=1" in rep

    def test_no_fields_still_works(self) -> None:
        q = CountUsers()
        assert isinstance(q, Query)

    def test_invalid_entity_raises(self) -> None:
        with pytest.raises(DomainException, match="TEntity for"):

            class _(Query[str, int]):
                pass

    def test_non_root_entity_field_raises(self) -> None:
        with pytest.raises(DomainException, match="non-root Entity"):

            class _(Query[User, User]):
                items: tuple[Entity, ...]

    def test_root_entity_field_allowed(self) -> None:
        class _(Query[User, User]):
            user: User

    def test_result_must_include_root_entity(self) -> None:
        with pytest.raises(DomainException, match="must include a RootEntity"):

            class _(Query[User, int]):
                pass

    def test_result_with_nested_root_entity_allowed(self) -> None:
        class _(Query[User, tuple[int, User | None]]):
            pass

    def test_command_not_affected_by_result_check(self) -> None:
        class _(Command[User, int]):
            pass


class TestCommandHandler:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            CommandHandler[CreateUser]()

    def test_without_handle_is_abstract(self) -> None:
        class Incomplete(CommandHandler[CreateUser]):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_handler_works(self) -> None:
        h = CreateUserHandler()
        cmd = CreateUser(name="Alice", email="a@b.com")
        result = h.handle(cmd)
        assert isinstance(result, User)
        assert result.name == "Alice"

    def test_different_entity_types(self) -> None:
        h = CreateOrderHandler()
        cmd = CreateOrder(total=49.99)
        result = h.handle(cmd)
        assert isinstance(result, Order)
        assert result.total == 49.99

    def test_inheritance(self) -> None:
        h = BaseCommandHandler()
        cmd = CreateUser(name="Test", email="t@t.com")
        result = h.handle(cmd)
        assert result.id == IntId(value=99)


class TestQueryHandler:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            QueryHandler[GetUser]()

    def test_without_handle_is_abstract(self) -> None:
        class Incomplete(QueryHandler[GetUser]):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_handler_works(self) -> None:
        h = GetUserHandler()
        result = h.handle(GetUser(user_id=1))
        assert result is not None
        assert result.name == "Alice"

    def test_returns_none_when_not_found(self) -> None:
        h = GetUserHandler()
        result = h.handle(GetUser(user_id=999))
        assert result is None

    def test_page_count(self) -> None:
        h = CountUsersHandler()
        result = h.handle(CountUsers())
        count, user = result
        assert count == 42
        assert user.id == IntId(value=1)
