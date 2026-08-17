# Policy System

Policies are independent application services. Enforcement is explicit and does
not belong to a `UseCase` or `Projection`, but a policy handler runs inside the
caller's transaction when one is active.

## Contracts And Handlers

`PolicyContract` is an immutable `BaseSealed` object containing the data needed
to authorize one decision:

```python
class AuthContract(PolicyContract):
    user_id: str


class AuthHandler(PolicyHandler[AuthContract]):
    def handle(self, contract: AuthContract) -> None:
        if contract.user_id != "allowed":
            raise PermissionError("not authenticated")
```

`PolicyPort` is the application-facing handler port. `PolicyHandler` is its
infrastructure implementation and may declare required dependencies such as
`QueryPort`, `CommandPort`, or other ports. Async variants are
available as `AsyncPolicyPort` and `AsyncPolicyHandler`.

## Manager

The container creates a manager from all registered policy handlers:

```python
policies = container.policy_manager()
```

The caller supplies the contracts required by the current decision:

```python
policies.enforce(auth_contract, admin_contract)  # AND
policies.enforce(auth_contract | admin_contract)  # OR
policies.enforce((auth_contract & ownership_contract) | admin_contract)
```

Multiple contracts passed directly to `enforce()` are joined with AND. Contracts
can be combined with `&` and `|`, including nested expressions. The expression
is an immutable `BaseSealed` value; its implementation is not part of the
caller-facing interface.

Each group is evaluated in declaration order. A group succeeds when every
policy in it succeeds. The expression succeeds when at least one group
succeeds. If all groups fail, `PolicyEnforcementError` contains the failures.

Direct `enforce()` is preferred over a context manager. Authorization needs
explicit contracts, and a context manager would only defer the same operation
and make sync/async behavior less clear.

## Container

Policy handlers share the handler registry with command/query handlers:

```python
container = AdapterContainer(handlers=[AuthHandler])
policies = container.policy_manager()
```

The manager resolves each contract by its concrete type and invokes the
matching handler. It does not alter `UseCase` or `Projection` construction and
does not run policies implicitly.

Handlers can be constructed without a container:

```python
policy = OwnerHandler(documents=document_query_handler)
policies = PolicyManager(policy)

with Transaction():
    policies.enforce(owner_contract)
    use_case.run()
```

The container is an optional convenience that adapts policy handlers and their
handler dependencies before the manager is created.
