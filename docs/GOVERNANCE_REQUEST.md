# Governance request and approval attestation

`govengine.governance.GovernanceRequest` is the canonical v1 input for the
next governance-decision flow. It binds one operation step and attempt to a
compiled policy pack, bounded execution facts, requested scope, runtime/lease
identity and optional approval.

`GovernanceRequest` is not a decision, execution permit, runtime claim, receipt
or SCLite truth artifact. G2-A intentionally does not add connector I/O,
consume-once storage, lease ownership or a second runtime permit.

## Digest ownership

GovEngine recomputes supplied digests when the complete GovEngine-owned record
is available:

- compiled policy pack;
- bounded execution facts;
- requested scope;
- embedded `ApprovalAttestation`.

The execution-spec, raw-payload and fencing-token digests are opaque bindings
owned by RExecOp. GovEngine validates their `sha256:<64 lowercase hex>` shape
and preserves them in the request subject; it does not claim access to or
verification of the underlying bytes.

The request subject digest excludes the approval itself, avoiding a circular
digest. It includes transaction, operation, step, attempt, policy, execution,
scope, side-effect, runtime, lease and fencing bindings. An approval for a
different subject fails closed.

## Approval validation

`ApprovalAttestation` identifies one approver and binds the exact:

- operation, step and attempt;
- execution spec and bounded execution facts;
- requested target scope;
- policy pack and policy epoch;
- approved side-effect class;
- validity window and revocation reference.

`validate_approval_attestation()` requires an explicit `ApprovalTrustPolicy`
and host-provided `ApprovalRevocationPort`. It rejects subject drift, an
untrusted approver/role/domain, a not-yet-valid or expired attestation, a
missing signature reference when policy requires one, and a revoked approval.

A signature reference is only a reference. G2-A does not claim cryptographic
signature verification from its presence. Production signature verification
must use the existing host-provided signing/verifier boundary before a future
`GovernanceDecision` can authorize a mutation.

## Legacy boundary

`GovApprovalRequest` remains a request for an approval workflow, not evidence
that approval occurred. `RuntimeAdmissionResult` remains a compatibility
adapter and is not extended by this contract. Opaque refs, admission digests,
manual booleans and strings containing `approval` are not accepted as an
`ApprovalAttestation`.
