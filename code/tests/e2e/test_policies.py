from __future__ import annotations

import asyncio

from aod.application import PolicyContract
from aod.infrastructure import AdapterContainer, PolicyHandler
from aod.infrastructure.async_ import PolicyHandler as AsyncPolicyHandler


class AccessContract(PolicyContract):
    user_id: str


class AccessHandler(PolicyHandler[AccessContract]):
    def handle(self, contract: AccessContract) -> None:
        if contract.user_id != "allowed":
            raise PermissionError("access denied")


class AsyncAccessHandler(AsyncPolicyHandler[AccessContract]):
    async def handle(self, contract: AccessContract) -> None:
        if contract.user_id != "allowed":
            raise PermissionError("access denied")


def test_container_builds_policy_manager_from_policy_handlers() -> None:
    container = AdapterContainer(handlers=[AccessHandler])

    manager = container.policy_manager()

    manager.enforce(AccessContract(user_id="allowed"))


def test_container_builds_async_policy_manager_from_policy_handlers() -> None:
    container = AdapterContainer(handlers=[AsyncAccessHandler])

    manager = container.async_policy_manager()

    async def run() -> None:
        await manager.enforce(AccessContract(user_id="allowed"))

    asyncio.run(run())
