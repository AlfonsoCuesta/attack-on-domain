from __future__ import annotations

from typing import Any, get_type_hints

from aod._internal.application.contracts import PolicyContract, PolicyExpression
from aod._internal.application.contracts.contracts import _PolicyOperator
from aod._internal.application.handler import AsyncPolicyPort, PolicyPort
from aod._internal.core.application_exception import PolicyEnforcementError
from aod._internal.core.async_utils import should_await

PolicyHandler = PolicyPort[Any] | AsyncPolicyPort[Any]
PolicyInput = PolicyContract | PolicyExpression


def _contract_type(handler: PolicyHandler) -> type[PolicyContract]:
    hints = get_type_hints(type(handler).handle)
    for parameter_type in hints.values():
        if isinstance(parameter_type, type) and issubclass(parameter_type, PolicyContract):
            return parameter_type
    raise TypeError(f"Cannot determine policy contract for {type(handler).__name__}")


def _validate_input(value: object) -> PolicyInput:
    if isinstance(value, (PolicyContract, PolicyExpression)):
        return value
    raise TypeError(f"Expected PolicyContract or PolicyExpression, got {type(value).__name__}")


class _PolicyManagerBase:
    def __init__(self, *handlers: PolicyHandler) -> None:
        self._handlers: dict[type[PolicyContract], PolicyHandler] = {}
        for handler in handlers:
            contract_type = _contract_type(handler)
            if contract_type in self._handlers:
                raise ValueError(f"Duplicate policy handler for {contract_type.__name__}")
            self._handlers[contract_type] = handler

    def _root(self, requirements: tuple[PolicyInput, ...]) -> PolicyInput:
        if not requirements:
            raise ValueError("At least one policy contract is required")
        values = tuple(_validate_input(requirement) for requirement in requirements)
        root = values[0]
        for value in values[1:]:
            root = PolicyExpression(left=root, right=value, operator=_PolicyOperator.AND)
        return root

    def _handler_for(self, contract: PolicyContract) -> PolicyHandler:
        try:
            return self._handlers[type(contract)]
        except KeyError as error:
            raise TypeError(
                f"No policy handler registered for {type(contract).__name__}"
            ) from error

    def _enforce_node(self, node: PolicyInput) -> None:
        if isinstance(node, PolicyContract):
            self._handler_for(node).handle(node)
            return
        if node.operator is _PolicyOperator.AND:
            try:
                self._enforce_node(_validate_input(object.__getattribute__(node, "left")))
                self._enforce_node(_validate_input(object.__getattribute__(node, "right")))
            except Exception as error:
                raise PolicyEnforcementError([error]) from error
            return
        errors: list[Exception] = []
        for child in (
            object.__getattribute__(node, "left"),
            object.__getattribute__(node, "right"),
        ):
            try:
                self._enforce_node(_validate_input(child))
                return
            except Exception as error:
                errors.append(error)
        raise PolicyEnforcementError(errors)

    async def _enforce_node_async(self, node: PolicyInput) -> None:
        if isinstance(node, PolicyContract):
            await should_await(self._handler_for(node).handle(node))
            return
        if node.operator is _PolicyOperator.AND:
            try:
                await self._enforce_node_async(
                    _validate_input(object.__getattribute__(node, "left"))
                )
                await self._enforce_node_async(
                    _validate_input(object.__getattribute__(node, "right"))
                )
            except Exception as error:
                raise PolicyEnforcementError([error]) from error
            return
        errors: list[Exception] = []
        for child in (
            object.__getattribute__(node, "left"),
            object.__getattribute__(node, "right"),
        ):
            try:
                await self._enforce_node_async(_validate_input(child))
                return
            except Exception as error:
                errors.append(error)
        raise PolicyEnforcementError(errors)


class PolicyManager(_PolicyManagerBase):
    def enforce(self, *requirements: PolicyInput) -> None:
        self._enforce_node(self._root(requirements))


class AsyncPolicyManager(_PolicyManagerBase):
    async def enforce(self, *requirements: PolicyInput) -> None:
        await self._enforce_node_async(self._root(requirements))
