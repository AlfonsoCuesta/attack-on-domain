#!/usr/bin/env python3
"""Test script to generate docs and verify zensical site works."""

from pathlib import Path
import subprocess
import sys

from aod.domain import RootEntity, ValueObject, Field as AodField, BoundedContext
from aod.events import Event
from aod.application import UseCase, Port, Command, Query
from aod._internal.infrastructure.session import Session
from aod.infrastructure import (
    ReadProjection,
    WriteProjection,
    CommandHandler,
    ReadModel,
    WriteModel,
)
from aod.testing.doubles import SpySession
from aod.docs import DocApp, DocInfra, generate_docs


class PetId(ValueObject):
    value: str


class PetName(ValueObject):
    value: str = AodField(description="Display name of the pet")


class Pet(RootEntity):
    id: PetId
    name: PetName
    species: str = AodField(description="Animal species")


class PetCreated(Event):
    pet_id: str
    name: str


class PetClient(Port):
    def save(self, pet: Pet) -> None: ...

    def find(self, pet_id: str) -> Pet | None: ...


PetContext = BoundedContext(aggregate_roots=[Pet], name="pets")


class CreatePet(Command[Pet, None]):
    pet_id: str = AodField(description="Unique identifier")
    name: str
    species: str


class GetPet(Query[Pet, Pet | None]):
    pet_id: str


class CreatePetUseCase(UseCase):
    pet_client: PetClient

    def run(self, pet_id: str, name: str, species: str) -> None:
        """Create a new pet in the system."""
        pass


class PetReadModel(ReadModel):
    pet_id: str


class PetListProjection(ReadProjection):
    def read(self, model: PetReadModel) -> list[Pet]:
        return []


class PetWriteModel(WriteModel):
    pet_id: str
    name: str


class PetUpdateProjection(WriteProjection):
    def write(self, model: PetWriteModel) -> None:
        pass


class SqlPetClient(PetClient):
    def save(self, pet: Pet) -> None: ...

    def find(self, pet_id: str) -> Pet | None: ...


class CreatePetHandler(CommandHandler[CreatePet]):
    session: Session

    def handle(self, command: CreatePet) -> None:
        pass


class PetNotFound(Exception):
    """Raised when a pet is not found."""


def main() -> None:
    output_dir = Path(__file__).parent / "tmp"

    print("Generating docs...")
    result = generate_docs(
        apps=[
            DocApp(
                name="Pet Store",
                description="Sistema de tienda de mascotas",
                bounded_contexts=[PetContext],
                use_cases=[CreatePetUseCase],
                commands=[CreatePet],
                queries=[GetPet],
                ports=[PetClient],
                infra=DocInfra(
                    sessions=[SpySession],
                    handlers=[CreatePetHandler],
                    projections=[PetListProjection, PetUpdateProjection],
                    port_impls=[SqlPetClient],
                    exceptions=[PetNotFound],
                ),
            )
        ],
        output_dir=str(output_dir),
    )
    print(f"Generated at: {result}")

    print("\nGenerated files:")
    for f in sorted(result.rglob("*.md")):
        print(f"  {f.relative_to(result)}")

    print("\nRunning zensical build...")
    proc = subprocess.run(
        ["uv", "run", "zensical", "build", "--clean"],
        cwd=str(result),
        capture_output=True,
        text=True,
    )
    print(proc.stdout)
    if proc.stderr:
        print("STDERR:", proc.stderr)

    if proc.returncode == 0:
        print("\nBuild successful!")
    else:
        print(f"\nBuild failed with return code {proc.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
