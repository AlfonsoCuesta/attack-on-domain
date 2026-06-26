from __future__ import annotations

import pytest
from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler import CommandPort as AppCommandPort
from aod._internal.application.handler import QueryPort as AppQueryPort
from aod._internal.application.port import Port
from aod._internal.application.use_case import UseCase
from aod._internal.core.application_exception import InvalidUseCasePortFieldError
from aod._internal.domain.entity import RootEntity
from aod._internal.domain.entity_id import EntityId
from aod._internal.infrastructure.handlers import CommandHandler, QueryHandler
from aod._internal.infrastructure.handlers.handlers import AsyncCommandHandler
from aod._internal.infrastructure.projection.projection import ProjectionBase
from aod._internal.infrastructure.session import AsyncSession, Session
from aod.domain import Field


class IntId(EntityId):
    value: int


class User(RootEntity):
    id: IntId = Field(id=True)
    name: str


class SaveUser(Command[User, None]):
    user_id: str


class GetUser(Query[User, User | None]):
    user_id: str


class InfraSaveHandler(CommandHandler[SaveUser]):
    session: Session

    def handle(self, command: SaveUser) -> None:
        pass


class InfraGetHandler(QueryHandler[GetUser]):
    session: Session

    def handle(self, query: GetUser) -> User | None:
        return None


class InfraAsyncSaveHandler(AsyncCommandHandler[SaveUser]):
    session: Session

    async def handle(self, command: SaveUser) -> None:
        pass


class FakePort(Port):
    pass


class TestUseCaseFieldValidation:
    def test_custom_port_field_is_accepted(self) -> None:
        class _MyUseCase(UseCase):
            my_port: FakePort

            def run(self) -> None:
                pass

        assert "my_port" in _MyUseCase.__model_fields__

    def test_app_sync_handler_field_is_accepted(self) -> None:
        class _MyUseCase(UseCase):
            save_handler: AppCommandPort[SaveUser]

            def run(self) -> None:
                pass

        assert "save_handler" in _MyUseCase.__model_fields__

    def test_app_query_handler_field_is_accepted(self) -> None:
        class _MyUseCase(UseCase):
            get_handler: AppQueryPort[GetUser]

            def run(self) -> None:
                pass

        assert "get_handler" in _MyUseCase.__model_fields__

    def test_infra_sync_handler_field_rejected(self) -> None:
        with pytest.raises(InvalidUseCasePortFieldError, match="save_handler"):

            class _MyUseCase(UseCase):
                save_handler: InfraSaveHandler

                def run(self) -> None:
                    pass

    def test_infra_async_handler_field_rejected(self) -> None:
        with pytest.raises(InvalidUseCasePortFieldError, match="save_handler"):

            class _MyUseCase(UseCase):
                save_handler: InfraAsyncSaveHandler

                def run(self) -> None:
                    pass

    def test_non_port_field_rejected(self) -> None:
        with pytest.raises(InvalidUseCasePortFieldError, match="bad_field"):

            class _MyUseCase(UseCase):
                bad_field: str

                def run(self) -> None:
                    pass

    def test_primitive_field_rejected(self) -> None:
        with pytest.raises(InvalidUseCasePortFieldError, match="count"):

            class _MyUseCase(UseCase):
                count: int

                def run(self) -> None:
                    pass

    def test_list_field_rejected(self) -> None:
        with pytest.raises(InvalidUseCasePortFieldError, match="items"):

            class _MyUseCase(UseCase):
                items: list[str]

                def run(self) -> None:
                    pass

    def test_field_without_type_hint_ignored(self) -> None:
        class _MyUseCase(UseCase):
            untyped = "value"

            def run(self) -> None:
                pass

    def test_session_field_rejected(self) -> None:
        with pytest.raises(InvalidUseCasePortFieldError, match="db"):

            class _MyUseCase(UseCase):
                db: Session

                def run(self) -> None:
                    pass

    def test_async_session_field_rejected(self) -> None:
        with pytest.raises(InvalidUseCasePortFieldError, match="db"):

            class _MyUseCase(UseCase):
                db: AsyncSession

                def run(self) -> None:
                    pass


class TestProjectionFieldValidation:
    def test_custom_port_field_is_accepted(self) -> None:
        class _MyProjection(ProjectionBase):
            my_port: FakePort

        assert "my_port" in _MyProjection.__model_fields__

    def test_infra_handler_field_rejected(self) -> None:
        with pytest.raises(InvalidUseCasePortFieldError, match="handler"):

            class _MyProjection(ProjectionBase):
                handler: InfraSaveHandler

    def test_app_handler_field_rejected(self) -> None:
        with pytest.raises(InvalidUseCasePortFieldError, match="handler"):

            class _MyProjection(ProjectionBase):
                handler: AppCommandPort[SaveUser]

    def test_non_port_field_rejected(self) -> None:
        with pytest.raises(InvalidUseCasePortFieldError, match="bad_field"):

            class _MyProjection(ProjectionBase):
                bad_field: int
