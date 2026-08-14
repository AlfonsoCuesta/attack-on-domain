from __future__ import annotations

import asyncio

import pytest

from aod._internal.application.policy import (
    AsyncPolicyManager,
    PolicyContract,
    PolicyExpression,
    PolicyManager,
)
from aod._internal.core.application_exception import PolicyEnforcementError
from aod._internal.infrastructure.handlers import AsyncPolicyHandler, PolicyHandler


class AuthContract(PolicyContract):
    user_id: str


class AdminContract(PolicyContract):
    user_id: str


class AuthHandler(PolicyHandler[AuthContract]):
    def handle(self, contract: AuthContract) -> None:
        if contract.user_id != "allowed":
            raise PermissionError("not authenticated")


class AdminHandler(PolicyHandler[AdminContract]):
    def handle(self, contract: AdminContract) -> None:
        if contract.user_id != "admin":
            raise PermissionError("not an administrator")


class AsyncAuthHandler(AsyncPolicyHandler[AuthContract]):
    async def handle(self, contract: AuthContract) -> None:
        if contract.user_id != "allowed":
            raise PermissionError("not authenticated")


class AsyncAdminHandler(AsyncPolicyHandler[AdminContract]):
    async def handle(self, contract: AdminContract) -> None:
        if contract.user_id != "admin":
            raise PermissionError("not an administrator")


def test_manager_enforces_contracts_as_and_by_default() -> None:
    manager = PolicyManager(AuthHandler(), AdminHandler())

    manager.enforce(AuthContract(user_id="allowed"), AdminContract(user_id="admin"))


def test_manager_can_enforce_only_the_dynamic_contracts_requested() -> None:
    manager = PolicyManager(AuthHandler(), AdminHandler())

    manager.enforce(AuthContract(user_id="allowed"))


def test_contract_operators_build_sealed_expressions() -> None:
    auth = AuthContract(user_id="allowed")
    admin = AdminContract(user_id="admin")

    expression = (auth & admin) | auth

    assert isinstance(expression, PolicyExpression)


def test_manager_enforces_or_expression() -> None:
    manager = PolicyManager(AuthHandler(), AdminHandler())

    manager.enforce(AuthContract(user_id="allowed") | AdminContract(user_id="user"))


def test_manager_reports_when_all_or_branches_fail() -> None:
    manager = PolicyManager(AuthHandler(), AdminHandler())

    with pytest.raises(PolicyEnforcementError) as error:
        manager.enforce(AuthContract(user_id="denied") | AdminContract(user_id="user"))

    assert len(error.value.errors) == 2


def test_manager_reports_failed_and_expression() -> None:
    manager = PolicyManager(AuthHandler(), AdminHandler())

    with pytest.raises(PolicyEnforcementError):
        manager.enforce(AuthContract(user_id="denied"), AdminContract(user_id="admin"))


def test_manager_rejects_empty_requirements() -> None:
    manager = PolicyManager(AuthHandler())

    with pytest.raises(ValueError):
        manager.enforce()


def test_manager_rejects_invalid_requirements() -> None:
    manager = PolicyManager(AuthHandler())

    with pytest.raises(TypeError):
        manager.enforce(object())  # ty:ignore[invalid-argument-type]


def test_manager_rejects_unknown_contract_handler() -> None:
    manager = PolicyManager(AuthHandler())

    with pytest.raises(TypeError, match="AdminContract"):
        manager.enforce(AdminContract(user_id="admin"))


def test_manager_rejects_duplicate_handlers() -> None:
    with pytest.raises(ValueError, match="AuthContract"):
        PolicyManager(AuthHandler(), AuthHandler())


def test_manager_rejects_handlers_without_contract_types() -> None:
    class InvalidHandler:
        def handle(self, value: object) -> None:
            pass

    with pytest.raises(TypeError):
        PolicyManager(InvalidHandler())  # ty:ignore[invalid-argument-type]


def test_policy_handlers_do_not_use_command_query_cache_wrapping() -> None:
    assert not hasattr(AuthHandler.handle, "__aod_handler_cache_wrapped__")


def test_async_manager_enforces_async_handlers() -> None:
    manager = AsyncPolicyManager(AsyncAuthHandler())

    async def run() -> None:
        await manager.enforce(AuthContract(user_id="allowed"))

    asyncio.run(run())


def test_async_manager_reports_failed_and_expression() -> None:
    manager = AsyncPolicyManager(AsyncAuthHandler(), AsyncAdminHandler())

    async def run() -> None:
        await manager.enforce(AuthContract(user_id="allowed"), AdminContract(user_id="admin"))
        await manager.enforce(AuthContract(user_id="allowed") | AdminContract(user_id="user"))
        with pytest.raises(PolicyEnforcementError):
            await manager.enforce(AuthContract(user_id="denied"), AdminContract(user_id="admin"))
        with pytest.raises(PolicyEnforcementError):
            await manager.enforce(AuthContract(user_id="denied") | AdminContract(user_id="user"))

    asyncio.run(run())
