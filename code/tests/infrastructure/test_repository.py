from __future__ import annotations

import pytest
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.domain_exception import (
    DomainException,
    ModelValidationError,
    MutationForbiddenException,
)
from aod._internal.core.infrastructure_exception import (
    HandlerResultTypeError,
    InfrastructureException,
)
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.type_checks.contract_checks import extract_root_entity
from aod._internal.type_checks.handler_checks import extract_handler_type, validate_handler_type
from aod.application import Command, Query
from aod.infrastructure import CommandHandler, QueryHandler, Repository


class User(RootEntity):
    id: int
    name: str
    email: str


class Order(RootEntity):
    id: int
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
    def handle(self, cmd: CreateUser) -> User:
        return User(id=1, name=cmd.name, email=cmd.email)


class GetUserHandler(QueryHandler[GetUser]):
    def handle(self, query: GetUser) -> User | None:
        if query.user_id == 1:
            return User(id=1, name="Alice", email="a@b.com")
        return None


class DeleteUserHandler(CommandHandler[DeleteUser]):
    def handle(self, cmd: DeleteUser) -> None: ...


class CountUsersHandler(QueryHandler[CountUsers]):
    def handle(self, query: CountUsers) -> tuple[int, User]:
        return (42, User(id=1, name="dummy", email="d@d.com"))


class CreateOrderHandler(CommandHandler[CreateOrder]):
    def handle(self, cmd: CreateOrder) -> Order:
        return Order(id=1, total=cmd.total)


class BaseCommandHandler(CommandHandler[CreateUser]):
    def handle(self, cmd: CreateUser) -> User:
        return User(id=99, name=cmd.name, email=cmd.email)


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
        assert result.id == 99


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
        assert user.id == 1


class TestRepository:
    def test_empty_init(self) -> None:
        class EmptyRepo(Repository[User]):
            pass

        repo = EmptyRepo()
        assert repo is not None

    def test_dispatches_command(self) -> None:
        class UserRepo(Repository[User]):
            pass

        repo = UserRepo(command_handlers=[CreateUserHandler()])
        result = repo.command(CreateUser(name="Alice", email="a@b.com"))
        assert isinstance(result, User)
        assert result.name == "Alice"

    def test_dispatches_query(self) -> None:
        class UserRepo(Repository[User]):
            pass

        repo = UserRepo(query_handlers=[GetUserHandler()])
        result = repo.query(GetUser(user_id=1))
        assert isinstance(result, User | None)

    def test_unknown_command_raises(self) -> None:
        class UserRepo(Repository[User]):
            pass

        repo = UserRepo()
        cmd = CreateUser(name="Alice", email="a@b.com")
        with pytest.raises(
            InfrastructureException, match="No command handler registered for CreateUser"
        ):
            repo.command(cmd)

    def test_unknown_query_raises(self) -> None:
        class UserRepo(Repository[User]):
            pass

        repo = UserRepo()
        with pytest.raises(
            InfrastructureException, match="No query handler registered for GetUser"
        ):
            repo.query(GetUser(user_id=1))

    def test_duplicate_command_handler_raises(self) -> None:
        class UserRepo(Repository[User]):
            pass

        with pytest.raises(InfrastructureException, match="Duplicate handler for CreateUser"):
            UserRepo(command_handlers=[CreateUserHandler(), CreateUserHandler()])

    def test_duplicate_query_handler_raises(self) -> None:
        class UserRepo(Repository[User]):
            pass

        with pytest.raises(InfrastructureException, match="Duplicate handler for GetUser"):
            UserRepo(query_handlers=[GetUserHandler(), GetUserHandler()])

    def test_multiple_handlers(self) -> None:
        class UserRepo(Repository[User]):
            pass

        repo = UserRepo(
            command_handlers=[CreateUserHandler(), DeleteUserHandler()],
            query_handlers=[GetUserHandler(), CountUsersHandler()],
        )

        user = repo.command(CreateUser(name="Charlie", email="c@d.com"))
        assert user is not None
        assert user.name == "Charlie"

        found = repo.query(GetUser(user_id=1))
        assert found is not None
        assert found.name == "Alice"

        count = repo.query(CountUsers())
        assert count[0] == 42
        assert count[1].id == 1

        result = repo.command(DeleteUser(user_id=5))
        assert result is None

    def test_many_commands_do_not_share_state(self) -> None:
        class UserRepo(Repository[User]):
            pass

        repo = UserRepo(command_handlers=[CreateUserHandler()])

        user1 = repo.command(CreateUser(name="A", email="a@a.com"))
        user2 = repo.command(CreateUser(name="B", email="b@b.com"))
        assert user1.id == 1
        assert user1.name == "A"
        assert user2.name == "B"

    def test_repository_marker(self) -> None:
        class UserRepo(Repository[User]):
            pass

        repo = UserRepo()
        assert isinstance(repo, Repository)
        assert isinstance(repo, BaseSealed)

    def test_with_handler_inheritance(self) -> None:
        class UserRepo(Repository[User]):
            pass

        repo = UserRepo(command_handlers=[BaseCommandHandler()])
        user = repo.command(CreateUser(name="Test", email="t@t.com"))
        assert user.id == 99

    def test_commands_and_queries_independent(self) -> None:
        class UserRepo(Repository[User]):
            pass

        repo = UserRepo(
            command_handlers=[CreateUserHandler()],
            query_handlers=[CountUsersHandler()],
        )

        user = repo.command(CreateUser(name="X", email="x@y.com"))
        assert user is not None
        assert user.name == "X"

        count = repo.query(CountUsers())
        assert count[0] == 42
        assert count[1].id == 1

    def test_no_queried_type_leak(self) -> None:
        class OrderRepo(Repository[Order]):
            pass

        repo = OrderRepo(command_handlers=[CreateOrderHandler()])
        order = repo.command(CreateOrder(total=99.99))
        assert isinstance(order, Order)
        assert order.total == 99.99

    def test_query_handler_in_command_list_raises(self) -> None:
        class UserRepo(Repository[User]):
            pass

        with pytest.raises(ModelValidationError):
            UserRepo(command_handlers=[GetUserHandler()])  # type: ignore

    def test_command_handler_in_query_list_raises(self) -> None:
        class UserRepo(Repository[User]):
            pass

        with pytest.raises(ModelValidationError):
            UserRepo(query_handlers=[CreateUserHandler()])  # type: ignore

    def test_unbound_handler_raises(self) -> None:
        class BadHandler(CommandHandler):
            def handle(self, cmd):
                return None

        with pytest.raises(DomainException):
            extract_handler_type(BadHandler(), (CommandHandler, QueryHandler))

    def test_handler_for_wrong_entity_type(self) -> None:
        class OrderHandler(CommandHandler[CreateOrder]):
            def handle(self, cmd: CreateOrder) -> Order:
                return Order(id=1, total=cmd.total)

        class UserRepo(Repository[User]):
            pass

        with pytest.raises(
            DomainException, match="handles entity Order, but repository is for entity User"
        ):
            UserRepo(command_handlers=[OrderHandler()])


class TestContractChecks:
    def test_validate_fields_no_entity_name_error(self) -> None:
        class ForwaredRefCmd(Command[User, User]):
            items: "NonExistentType"  # type: ignore  # noqa: F821

        # Class creation succeeds because NameError is caught

    def test_validate_result_no_result_type(self) -> None:
        class BareQuery(Query):
            pass

        assert issubclass(BareQuery, Query)

    def test_extract_root_entity_returns_none(self) -> None:
        class NotARepo(BaseSealed):
            pass

        result = extract_root_entity(NotARepo())
        assert result is None

    def test_extract_root_entity_with_object(self) -> None:
        result = extract_root_entity(object())
        assert result is None


class TestHandlerChecks:
    def test_validate_handler_type_raises(self) -> None:
        class NotAHandler(BaseSealed):
            pass

        with pytest.raises(DomainException, match="does not handle"):
            validate_handler_type(NotAHandler(), CommandHandler)

        with pytest.raises(DomainException, match="does not handle"):
            validate_handler_type(NotAHandler(), QueryHandler)


class TestHandlerResultTypeError:
    def test_command_handler_wrong_result_type_raises(self) -> None:
        class BadCommandHandler(CommandHandler[CreateUser]):
            def handle(self, cmd: CreateUser) -> object:
                return "not a user"

        h = BadCommandHandler()
        with pytest.raises(HandlerResultTypeError) as exc:
            h.handle(CreateUser(name="x", email="x@x.com"))
        assert "BadCommandHandler" in str(exc.value)

    def test_query_handler_wrong_result_type_raises(self) -> None:
        class BadQueryHandler(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> object:
                return 42

        h = BadQueryHandler()
        with pytest.raises(HandlerResultTypeError) as exc:
            h.handle(GetUser(user_id=1))
        assert "BadQueryHandler" in str(exc.value)

    def test_handler_returns_none_when_disallowed(self) -> None:
        class NoneReturningHandler(QueryHandler[GetUser]):
            def handle(self, query: GetUser) -> object:
                return None

        h = NoneReturningHandler()
        result = h.handle(GetUser(user_id=1))
        assert result is None
