import pytest
from aod.application import Command, Query
from aod.domain import RootEntity
from aod.infrastructure import CommandHandler, QueryHandler
from aod.infrastructure.async_ import CommandHandler as AsyncCommandHandler
from aod.infrastructure.async_ import QueryHandler as AsyncQueryHandler


class Pet(RootEntity):
    id: str
    name: str


class CreatePet(Command[Pet, None]):
    pet_id: str
    name: str


class GetPet(Query[Pet, Pet | None]):
    pet_id: str


class OtherCommand(Command[Pet, None]):
    value: str


class CreatePetHandler(CommandHandler[CreatePet]):
    def handle(self, command: CreatePet) -> None:
        pass


class GetPetHandler(QueryHandler[GetPet]):
    def handle(self, query: GetPet) -> Pet | None:
        return None


class AsyncCreatePetHandler(AsyncCommandHandler[CreatePet]):
    async def handle(self, command: CreatePet) -> None:
        pass


class AsyncGetPetHandler(AsyncQueryHandler[GetPet]):
    async def handle(self, query: GetPet) -> Pet | None:
        return None


class TestHandlerTypeCheck:
    def test_command_handler_accepts_correct_type(self) -> None:
        handler = CreatePetHandler()
        handler.handle(CreatePet(pet_id="1", name="test"))

    def test_command_handler_rejects_wrong_type(self) -> None:
        handler = CreatePetHandler()
        with pytest.raises(TypeError, match="Expected CreatePet, got OtherCommand"):
            handler.handle(OtherCommand(value="wrong"))  # type: ignore

    def test_query_handler_accepts_correct_type(self) -> None:
        handler = GetPetHandler()
        handler.handle(GetPet(pet_id="1"))

    def test_query_handler_rejects_wrong_type(self) -> None:
        handler = GetPetHandler()
        with pytest.raises(TypeError, match="Expected GetPet, got OtherCommand"):
            handler.handle(OtherCommand(value="wrong"))  # type: ignore

    async def test_async_command_handler_accepts_correct_type(self) -> None:
        handler = AsyncCreatePetHandler()
        await handler.handle(CreatePet(pet_id="1", name="test"))

    async def test_async_command_handler_rejects_wrong_type(self) -> None:
        handler = AsyncCreatePetHandler()
        with pytest.raises(TypeError, match="Expected CreatePet, got OtherCommand"):
            await handler.handle(OtherCommand(value="wrong"))  # type: ignore

    async def test_async_query_handler_accepts_correct_type(self) -> None:
        handler = AsyncGetPetHandler()
        await handler.handle(GetPet(pet_id="1"))

    async def test_async_query_handler_rejects_wrong_type(self) -> None:
        handler = AsyncGetPetHandler()
        with pytest.raises(TypeError, match="Expected GetPet, got OtherCommand"):
            await handler.handle(OtherCommand(value="wrong"))  # type: ignore
