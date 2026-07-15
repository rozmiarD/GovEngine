# Scope and capability bindings

G2-B separates what an operation requests from what policy and the runtime
independently allow or provide.

## Scope policy

`ScopePolicyBinding` carries a policy-pack/epoch binding, authenticated source
references, allowed target namespaces and bounded network policy. A requested
scope carries only:

- `target_namespace`;
- optional `requested_destination.scheme`;
- optional `requested_destination.effective_port`;
- optional `requested_destination.address_class`;
- optional opaque `origin_binding_digest`.

`evaluate_scope_policy()` rejects allowlist, redirect-policy,
`network_allowed` or private-network-policy fields supplied by the request.
It compares requested facts with the independent policy and returns a
deterministic `ScopeDecision`.

The scope decision is governance policy, not network enforcement. RExecOp
still owns DNS resolution/re-resolution, redirect handling, origin checks,
credential/header forwarding and the final pre-I/O network gate. GovEngine
does not claim SSRF or DNS-rebinding protection from bounded metadata alone.

## Capability compatibility

`OperationCapabilityRequirements` comes from the operation/profile/runbook
contract and must contain an explicit non-empty requirement set.

`CapabilityInventoryBinding` comes from the runtime registry and binds one
runtime instance and inventory epoch to explicit backend, side-effect and
capability sets. It requires source and attestation references and rejects
host registration/support booleans as certification evidence.

`evaluate_capability_compatibility()` checks:

```text
required capabilities subset of inventory capabilities
required backend class in inventory backend classes
side-effect class in inventory side-effect classes
```

It returns a deterministic `CapabilityCompatibilityDecision` with missing
capabilities and stable reason codes. GovEngine does not load plugins, inspect
installed packages or own the runtime registry. A reference is not by itself
cryptographic verification; the issuer/trust integration remains an explicit
later gate.

## GovernanceRequest binding

`GovernanceRequest v1` embeds all three full records and their supplied
digests. GovEngine recomputes each digest and additionally checks:

- scope policy pack and epoch match the request policy;
- requirements operation, step, spec and side effect match the request;
- inventory runtime instance matches the request runtime.

The request subject digest includes the three binding digests, so an existing
approval cannot be moved to another scope policy, requirement set or runtime
inventory.

`evaluate_governance()` includes both decision digests in
`GovernanceDecision`; a denied scope or incompatible inventory cannot produce
authorization.
