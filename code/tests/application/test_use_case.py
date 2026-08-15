from __future__ import annotations

from abc import abstractmethod

import pytest
from aod._internal.application.event_bus import EventBus
from aod._internal.application.logger import Logger
from aod._internal.application.transaction import Transaction
from aod._internal.core.application_exception import CommitOutsideUnitOfWorkError
from aod._internal.core.domain_exception import MutationForbiddenException
from aod._internal.core.fields.fields import PrivateField
from aod._internal.infrastructure.handlers.handlers import BaseHandler
from aod._internal.infrastructure.session import Session
from aod.application import UseCase
from aod.testing.doubles import spy_port
from tests.application._use_case_scenarios import Address, User, UserCreated


class CreateUser(UseCase):
    def run(self, user_id: int, name: str) -> None:
        user = User(id=user_id, name=name)
        user._event_emitter.emit(UserCreated(user_id=user.id, name=user.name))


def execute(use_case: UseCase, *args: object, **kwargs: object) -> object:
    with Transaction(operation=use_case):
        return use_case.run(*args, **kwargs)


def test_use_case_is_abstract() -> None:
    with pytest.raises(TypeError):
        UseCase()


def test_subclass_without_run_is_abstract() -> None:
    class Incomplete(UseCase):
        pass

    with pytest.raises(TypeError):
        Incomplete()


def test_run_has_no_implicit_transaction() -> None:
    use_case = CreateUser()
    use_case.run(user_id=1, name="Alice")
    assert use_case.events == []


def test_transaction_collects_events() -> None:
    use_case = CreateUser()
    execute(use_case, user_id=1, name="Alice")
    assert len(use_case.events) == 1
    assert use_case.events[0].user_id == 1


def test_transaction_replaces_events() -> None:
    use_case = CreateUser()
    execute(use_case, user_id=1, name="Alice")
    first = list(use_case.events)
    execute(use_case, user_id=2, name="Bob")
    assert len(first) == 1
    assert use_case.events[0].user_id == 2


def test_transaction_collects_events_on_failure() -> None:
    class Failing(UseCase):
        def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="Alice"))
            raise ValueError("boom")

    use_case = Failing()
    with pytest.raises(ValueError, match="boom"):
        execute(use_case)
    assert len(use_case.events) == 1


def test_events_are_immutable() -> None:
    use_case = CreateUser()
    execute(use_case, user_id=1, name="Alice")
    with pytest.raises(MutationForbiddenException):
        use_case.events.append(UserCreated(user_id=2, name="Bob"))


def test_use_case_can_have_complex_inputs() -> None:
    class Complex(UseCase):
        def run(self, user_id: int, address: Address) -> None:
            User(id=user_id, name="Alice", address=address)

    execute(Complex(), 1, Address(street="Main", city="Town"))


def test_post_init_runs() -> None:
    called: list[bool] = []

    class WithPostInit(UseCase):
        def __post_init__(self) -> None:
            called.append(True)

        def run(self) -> None:
            pass

    WithPostInit()
    assert called == [True]


class _Session(Session):
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)

    def begin(self) -> None:
        pass

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        self._rolled_back = True

    def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return True

    def execute(self, operation: object) -> object:
        return operation

    def query(self, operation: object) -> object:
        return operation


class _Handler(BaseHandler):
    session: _Session


class _CommitHandler(_Handler):
    def handle(self) -> None:
        self.session.commit()


def test_transaction_discovers_handler_sessions() -> None:
    session = _Session()
    handler = _Handler(session=session)

    class Save(UseCase):
        __skip_port_check__ = True
        save: _Handler

        def run(self) -> None:
            pass

    use_case = Save(save=handler)
    execute(use_case)
    assert session._committed


def test_handler_cannot_commit_session_during_operation() -> None:
    session = _Session()
    handler = _CommitHandler(session=session)

    class Save(UseCase):
        __skip_port_check__ = True
        save: _CommitHandler

        def run(self) -> None:
            self.save.handle()

    with pytest.raises(CommitOutsideUnitOfWorkError):
        execute(Save(save=handler))
    assert session._rolled_back
    assert not session._committed


def test_transaction_uses_operation_logger_and_event_bus() -> None:
    class Emit(UseCase):
        logger: Logger
        event_bus: EventBus

        def run(self) -> None:
            self._event_emitter.emit(UserCreated(user_id=1, name="Alice"))

    logger = spy_port(Logger)()
    bus = spy_port(EventBus)()
    execute(Emit(logger=logger, event_bus=bus))
    assert logger.info.call_count == 2
    assert bus.publish.call_count == 1


def test_use_case_returns_value() -> None:
    class Sum(UseCase):
        def run(self, left: int, right: int) -> int:
            return left + right

    assert execute(Sum(), 2, 3) == 5


def test_inheritance_and_abstract_methods() -> None:
    class Abstract(UseCase):
        @abstractmethod
        def run(self) -> None: ...

    class Concrete(Abstract):
        def run(self) -> None:
            pass

    execute(Concrete())
