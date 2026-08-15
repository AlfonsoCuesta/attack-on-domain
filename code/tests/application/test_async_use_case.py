from __future__ import annotations

import pytest
from aod._internal.application.transaction import AsyncTransaction
from aod._internal.application.use_case import AsyncUseCase
from aod._internal.core.application_exception import CommitOutsideUnitOfWorkError
from aod._internal.core.event_emitter import Event
from aod._internal.core.fields.fields import PrivateField
from aod._internal.infrastructure.handlers.handlers import BaseHandler
from aod._internal.infrastructure.session import AsyncSession


class _Event(Event):
    value: str


class _Session(AsyncSession):
    _committed: bool = PrivateField(default=False)
    _rolled_back: bool = PrivateField(default=False)

    async def begin(self) -> None:
        pass

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        self._rolled_back = True

    async def close(self) -> None:
        pass

    def is_dirty(self) -> bool:
        return True

    async def execute(self, operation: object) -> object:
        return operation

    async def query(self, operation: object) -> object:
        return operation


class _Handler(BaseHandler):
    session: _Session


class _CommitHandler(_Handler):
    async def handle(self) -> None:
        await self.session.commit()


class Create(AsyncUseCase):
    async def run(self) -> None:
        self._event_emitter.emit(_Event(value="created"))


async def execute(use_case: AsyncUseCase) -> None:
    async with AsyncTransaction(operation=use_case):
        await use_case.run()


def test_async_use_case_is_abstract() -> None:
    with pytest.raises(TypeError):
        AsyncUseCase()


@pytest.mark.asyncio
async def test_async_run_has_no_implicit_transaction() -> None:
    use_case = Create()
    await use_case.run()
    assert use_case.events == []


@pytest.mark.asyncio
async def test_async_transaction_collects_events() -> None:
    use_case = Create()
    await execute(use_case)
    assert len(use_case.events) == 1


@pytest.mark.asyncio
async def test_async_transaction_discovers_handler_sessions() -> None:
    session = _Session()
    handler = _Handler(session=session)

    class Save(AsyncUseCase):
        __skip_port_check__ = True
        save: _Handler

        async def run(self) -> None:
            pass

    use_case = Save(save=handler)
    async with AsyncTransaction(operation=use_case):
        await use_case.run()
    assert session._committed


@pytest.mark.asyncio
async def test_async_handler_cannot_commit_session_during_operation() -> None:
    session = _Session()
    handler = _CommitHandler(session=session)

    class Save(AsyncUseCase):
        __skip_port_check__ = True
        save: _CommitHandler

        async def run(self) -> None:
            await self.save.handle()

    use_case = Save(save=handler)
    with pytest.raises(CommitOutsideUnitOfWorkError):
        async with AsyncTransaction(operation=use_case):
            await use_case.run()
    assert session._rolled_back
    assert not session._committed


@pytest.mark.asyncio
async def test_async_transaction_rolls_back_and_preserves_events() -> None:
    class Failing(AsyncUseCase):
        async def run(self) -> None:
            self._event_emitter.emit(_Event(value="before-failure"))
            raise ValueError("boom")

    use_case = Failing()
    with pytest.raises(ValueError, match="boom"):
        async with AsyncTransaction(operation=use_case):
            await use_case.run()
    assert len(use_case.events) == 1
